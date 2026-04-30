import math


import serial
import threading
import time
import struct
from dataclasses import dataclass, field


@dataclass
class BasicSensorData:
    bumper: int = 0
    wheel_drop: int = 0
    cliff: int = 0
    encoder_l: int = 0
    encoder_r: int = 0
    battery: int = 0
    updated_at: float = 0.0


@dataclass
class InertialSensorData:
    gyro_angle: float = 0.0
    gyro_rate: float = 0.0
    updated_at: float = 0.0


@dataclass
class OdometryState:
    x: float = 0.0
    y: float = 0.0
    theta: float = 0.0
    prev_left_ticks: int | None = None
    prev_right_ticks: int | None = None
    updated_at: float = 0.0


@dataclass
class KobukiState:
    timestamp: float = 0.0
    basic: BasicSensorData = field(default_factory=BasicSensorData)
    inertial: InertialSensorData = field(default_factory=InertialSensorData)
    odometry: OdometryState = field(default_factory=OdometryState)

class KobukiDriver:
    def __init__(self, port='/dev/ttyUSB0'):
        self.ser = None
        self.running = False
        self._state_lock = threading.Lock()
        self._serial_lock = threading.Lock()

        # Connection Settings
        try:
            self.ser = serial.Serial(port, 115200, timeout=0.1)
        except Exception as e:
            print(f"Error connecting to Kobuki: {e}")
            return

        # Robot Physical Constants (for Odom)
        self.TICK_TO_METER = 0.00008529
        self.WHEEL_BASE = 0.230 # 230mm

        # Structured state storage.
        self.state = KobukiState()

        # Start Background Thread
        self.running = True
        self.thread = threading.Thread(target=self._run)
        self.thread.daemon = True
        self.thread.start()

    def _run(self):
        """State machine to parse incoming serial bytes."""
        while self.running and self.ser is not None:
            # 1. Look for Header [0xAA, 0x55]
            if self.ser.read(1) == b'\xAA':
                if self.ser.read(1) == b'\x55':
                    # 2. Read Length
                    len_byte = self.ser.read(1)
                    if not len_byte: continue
                    length = ord(len_byte)
                    
                    # 3. Read Payload and Checksum
                    payload = self.ser.read(length)
                    checksum_byte = self.ser.read(1)
                    if not checksum_byte: continue
                    checksum = ord(checksum_byte)

                    # 4. Verify Checksum (XOR of Length + Payload)
                    calculated_cs = length
                    for b in payload:
                        calculated_cs ^= b
                    
                    if calculated_cs == checksum:
                        self._parse_payload(payload)

    def _parse_payload(self, payload):
        """Splits the payload into sub-packets based on ID."""
        i = 0
        packet_ts = time.time()
        with self._state_lock:
            self.state.timestamp = packet_ts
        
        while i < len(payload):
            sub_id = payload[i]
            sub_len = payload[i+1]
            sub_data = payload[i+2 : i+2+sub_len]

            if sub_id == 0x01: # Basic Sensor Data
                # Unpack 15 bytes of basic data
                # Bumper(1), WheelDrop(1), Cliff(1), L_Enc(2), R_Enc(2)...
                b, wd, c, l_enc, r_enc = struct.unpack('<BBBHH', sub_data[0:7])
                with self._state_lock:
                    self.state.basic.bumper = b
                    self.state.basic.wheel_drop = wd
                    self.state.basic.cliff = c
                    self.state.basic.encoder_l = l_enc
                    self.state.basic.encoder_r = r_enc
                    self.state.basic.battery = sub_data[11]
                    self.state.basic.updated_at = packet_ts
                    self._update_odom(l_enc, r_enc, packet_ts)

            elif sub_id == 0x0D: # Inertial Sensor (Gyro)
                angle, rate = struct.unpack('<hh', sub_data[0:4])
                with self._state_lock:
                    self.state.inertial.gyro_angle = angle / 100.0 # deg
                    self.state.inertial.gyro_rate = rate / 100.0   # deg/s
                    self.state.inertial.updated_at = packet_ts

            i += (2 + sub_len)

    def _update_odom(self, l_ticks, r_ticks, update_ts):
        """Calculates X, Y, Theta and handles 16-bit encoder wrap-around."""
        odom = self.state.odometry

        if odom.prev_left_ticks is None:
            odom.prev_left_ticks = l_ticks
            odom.prev_right_ticks = r_ticks
            odom.updated_at = update_ts
            return

        def handle_wrap(curr, prev):
            diff = curr - prev
            if diff > 32768: diff -= 65536
            elif diff < -32768: diff += 65536
            return diff

        dl = handle_wrap(l_ticks, odom.prev_left_ticks) * self.TICK_TO_METER
        dr = handle_wrap(r_ticks, odom.prev_right_ticks) * self.TICK_TO_METER
        
        # Differential Drive Kinematics
        dc = (dl + dr) / 2.0
        dw = (dr - dl) / self.WHEEL_BASE
        
        odom.x += dc * math.cos(odom.theta + dw/2.0)
        odom.y += dc * math.sin(odom.theta + dw/2.0)
        odom.theta += dw
        odom.updated_at = update_ts
        
        odom.prev_left_ticks = l_ticks
        odom.prev_right_ticks = r_ticks

    def drive(self, linear_vel, angular_vel):
        """
        linear_vel: mm/s
        angular_vel: rad/s
        """
        # Kobuki expects Speed (mm/s) and Radius (mm)
        # Radius = v / w
        if abs(angular_vel) < 0.001:
            radius = 0
        else:
            radius = int(linear_vel / angular_vel)
            # Clip radius to Kobuki limits
            if radius > 2500: radius = 0
            elif radius < -2500: radius = 0

        # Build Packet
        payload = bytearray([0x01, 0x04])
        payload += int(linear_vel).to_bytes(2, 'little', signed=True)
        payload += int(radius).to_bytes(2, 'little', signed=True)
        
        header = bytearray([0xAA, 0x55, len(payload)])
        packet = header + payload
        
        cs = len(payload)
        for b in payload: cs ^= b
        packet.append(cs)
        
        if self.ser is None:
            return

        with self._serial_lock:
            self.ser.write(packet)

    def get_state(self):
        """Returns a thread-safe copy of the latest flattened state."""
        with self._state_lock:
            return {
                "timestamp": self.state.timestamp,
                "bumper": self.state.basic.bumper,
                "wheel_drop": self.state.basic.wheel_drop,
                "cliff": self.state.basic.cliff,
                "encoder_l": self.state.basic.encoder_l,
                "encoder_r": self.state.basic.encoder_r,
                "battery": self.state.basic.battery,
                "gyro_angle": self.state.inertial.gyro_angle,
                "gyro_rate": self.state.inertial.gyro_rate,
                "x": self.state.odometry.x,
                "y": self.state.odometry.y,
                "theta": self.state.odometry.theta,
                "basic_timestamp": self.state.basic.updated_at,
                "inertial_timestamp": self.state.inertial.updated_at,
                "odometry_timestamp": self.state.odometry.updated_at,
            }

# --- Main Test Loop ---
if __name__ == "__main__":
    robot = KobukiDriver(port='/dev/ttyUSB0') # Change to your COM port
    
    try:
        while True:
            # Drive in a slow circle
            robot.drive(100, 0.5) 
            
            data = robot.get_state()
            print(f"Pos: {data['x']:.2f}, {data['y']:.2f} | Gyro: {data['gyro_angle']:.1f}")
            
            time.sleep(0.1) # 10Hz Loop
    except KeyboardInterrupt:
        robot.drive(0, 0)
        print("\nStopped.")
