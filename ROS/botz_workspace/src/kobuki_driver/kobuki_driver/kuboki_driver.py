# import rclpy
# from rclpy.node import Node
# from nav_msgs.msg import Odometry
# from sensor_msgs.msg import Imu
# from geometry_msgs.msg import Twist, TransformStamped, Quaternion
# from tf2_ros import TransformBroadcaster
import math


import serial
import threading
import time
import struct
# import math

class KobukiDriver:
    def __init__(self, port='/dev/ttyUSB0'):
        # Connection Settings
        try:
            self.ser = serial.Serial(port, 115200, timeout=0.1)
        except Exception as e:
            print(f"Error connecting to Kobuki: {e}")
            return

        # Robot Physical Constants (for Odom)
        self.TICK_TO_METER = 0.00008529
        self.WHEEL_BASE = 0.230 # 230mm

        # State Variables
        self.pos_x = 0.0
        self.pos_y = 0.0
        self.theta = 0.0
        self.prev_left_ticks = None
        self.prev_right_ticks = None

        # Data Storage for Fusion
        self.sensor_data = {
            "timestamp": 0,
            "bumper": 0,
            "wheel_drop": 0,
            "cliff": 0,
            "encoder_l": 0,
            "encoder_r": 0,
            "battery": 0,
            "gyro_angle": 0,
            "gyro_rate": 0
        }

        # Start Background Thread
        self.running = True
        self.thread = threading.Thread(target=self._run)
        self.thread.daemon = True
        self.thread.start()

    def _run(self):
        """State machine to parse incoming serial bytes."""
        while self.running:
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
        self.sensor_data["timestamp"] = time.time()
        
        while i < len(payload):
            sub_id = payload[i]
            sub_len = payload[i+1]
            sub_data = payload[i+2 : i+2+sub_len]

            if sub_id == 0x01: # Basic Sensor Data
                # Unpack 15 bytes of basic data
                # Bumper(1), WheelDrop(1), Cliff(1), L_Enc(2), R_Enc(2)...
                b, wd, c, l_enc, r_enc = struct.unpack('<BBBHH', sub_data[0:7])
                self.sensor_data.update({
                    "bumper": b, "wheel_drop": wd, "cliff": c,
                    "encoder_l": l_enc, "encoder_r": r_enc,
                    "battery": sub_data[11]
                })
                self._update_odom(l_enc, r_enc)

            elif sub_id == 0x0D: # Inertial Sensor (Gyro)
                angle, rate = struct.unpack('<hh', sub_data[0:4])
                self.sensor_data["gyro_angle"] = angle / 100.0 # deg
                self.sensor_data["gyro_rate"] = rate / 100.0   # deg/s

            i += (2 + sub_len)

    def _update_odom(self, l_ticks, r_ticks):
        """Calculates X, Y, Theta and handles 16-bit encoder wrap-around."""
        if self.prev_left_ticks is None:
            self.prev_left_ticks = l_ticks
            self.prev_right_ticks = r_ticks
            return

        def handle_wrap(curr, prev):
            diff = curr - prev
            if diff > 32768: diff -= 65536
            elif diff < -32768: diff += 65536
            return diff

        dl = handle_wrap(l_ticks, self.prev_left_ticks) * self.TICK_TO_METER
        dr = handle_wrap(r_ticks, self.prev_right_ticks) * self.TICK_TO_METER
        
        # Differential Drive Kinematics
        dc = (dl + dr) / 2.0
        dw = (dr - dl) / self.WHEEL_BASE
        
        self.pos_x += dc * math.cos(self.theta + dw/2.0)
        self.pos_y += dc * math.sin(self.theta + dw/2.0)
        self.theta += dw
        
        self.prev_left_ticks = l_ticks
        self.prev_right_ticks = r_ticks

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
        
        self.ser.write(packet)

    def get_state(self):
        """Returns fused-ready dictionary."""
        state = self.sensor_data.copy()
        state.update({
            "x": self.pos_x,
            "y": self.pos_y,
            "theta": self.theta
        })
        return state

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

# class KobukiROS2Node(Node):
#     def __init__(self):
#         super().__init__('kobuki_driver')
        
#         # Publishers
#         self.odom_pub = self.create_publisher(Odometry, '/odom', 10)
#         self.imu_pub  = self.create_publisher(Imu, '/imu/data', 10)
        
#         # TF broadcaster (odom -> base_link)
#         self.tf_broadcaster = TransformBroadcaster(self)
        
#         # Subscriber for velocity commands
#         self.cmd_sub = self.create_subscription(
#             Twist, '/cmd_vel', self.cmd_vel_callback, 10)
        
#         # Your driver (refactored to call publish methods on new data)
#         self.driver = KobukiDriver(port='/dev/ttyUSB0')
        
#         # Timer to publish at 10Hz
#         self.create_timer(0.1, self.publish_all)

#     def publish_all(self):
#         state = self.driver.get_state()
#         now = self.get_clock().now().to_msg()

#         # --- Odometry ---
#         odom = Odometry()
#         odom.header.stamp = now
#         odom.header.frame_id = 'odom'
#         odom.child_frame_id  = 'base_link'
        
#         odom.pose.pose.position.x = state['x']
#         odom.pose.pose.position.y = state['y']
#         # Convert theta to quaternion (rotation around Z)
#         odom.pose.pose.orientation = yaw_to_quaternion(state['theta'])
        
#         # Covariance (diagonal, tune these values!)
#         odom.pose.covariance[0]  = 0.01  # x
#         odom.pose.covariance[7]  = 0.01  # y
#         odom.pose.covariance[35] = 0.05  # yaw
#         odom.twist.covariance[0]  = 0.01
#         odom.twist.covariance[35] = 0.05
        
#         self.odom_pub.publish(odom)
        
#         # --- TF ---
#         tf = TransformStamped()
#         tf.header.stamp = now
#         tf.header.frame_id = 'odom'
#         tf.child_frame_id  = 'base_link'
#         tf.transform.translation.x = state['x']
#         tf.transform.translation.y = state['y']
#         tf.transform.rotation = yaw_to_quaternion(state['theta'])
#         self.tf_broadcaster.sendTransform(tf)

#         # --- IMU ---
#         imu = Imu()
#         imu.header.stamp = now
#         imu.header.frame_id = 'imu_link'
#         # Kobuki gyro = Z-axis only
#         imu.angular_velocity.z = math.radians(state['gyro_rate'])
#         imu.angular_velocity_covariance[8] = 0.02  # only Z valid
#         # No orientation from gyro alone — let robot_localization integrate it
#         imu.orientation_covariance[0] = -1  # signals "no orientation provided"
        
#         self.imu_pub.publish(imu)

#     def cmd_vel_callback(self, msg: Twist):
#         linear_mm_s  = msg.linear.x * 1000.0   # m/s -> mm/s
#         angular_rad_s = msg.angular.z
#         self.driver.drive(linear_mm_s, angular_rad_s)


# def yaw_to_quaternion(yaw) -> Quaternion:
#     q = Quaternion()
#     q.w = math.cos(yaw / 2.0)
#     q.z = math.sin(yaw / 2.0)
#     return q


# def main():
#     rclpy.init()
#     node = KobukiROS2Node()
#     rclpy.spin(node)
#     node.destroy_node()
#     rclpy.shutdown()



# if __name__ == '__main__':
#     main()