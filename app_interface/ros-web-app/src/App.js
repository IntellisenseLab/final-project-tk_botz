import React, { useEffect, useState, useRef, useCallback } from 'react';
import * as ROSLIB from 'roslib';
import { Power, MonitorPlay, Send } from 'lucide-react';
import './App.css';

const VirtualJoystick = ({ onMove, onStop }) => {
  const [position, setPosition] = useState({ x: 0, y: 0 });
  const [isDragging, setIsDragging] = useState(false);
  const joystickRef = useRef(null);
  
  // Configuration
  const maxRadius = 70; // Max pixel distance the stick can travel
  const maxLinear = 0.4; // Max m/s
  const maxAngular = 0.6; // Max rad/s

  const handlePointerDown = (e) => {
    setIsDragging(true);
    updateJoystick(e);
  };

  const handlePointerMove = (e) => {
    if (!isDragging) return;
    updateJoystick(e);
  };

  const handlePointerUp = () => {
    setIsDragging(false);
    setPosition({ x: 0, y: 0 });
    onStop(); // Publish zero velocities when released
  };

  const updateJoystick = useCallback((e) => {
    if (!joystickRef.current) return;
    
    const rect = joystickRef.current.getBoundingClientRect();
    const centerX = rect.left + rect.width / 2;
    const centerY = rect.top + rect.height / 2;

    // Support both mouse and touch events
    const clientX = e.touches ? e.touches[0].clientX : e.clientX;
    const clientY = e.touches ? e.touches[0].clientY : e.clientY;

    let dx = clientX - centerX;
    let dy = clientY - centerY;

    // Calculate distance from center
    const distance = Math.sqrt(dx * dx + dy * dy);

    // Clamp the joystick to the circular boundary
    if (distance > maxRadius) {
      const angle = Math.atan2(dy, dx);
      dx = Math.cos(angle) * maxRadius;
      dy = Math.sin(angle) * maxRadius;
    }

    setPosition({ x: dx, y: dy });

    // Mathematical Mapping to ROS Twist values
    // Browser Y is down (positive), so we invert dy for forward movement
    // Browser X is right (positive), so we invert dx for standard left-turn (CCW) rotation
    const linearVel = -(dy / maxRadius) * maxLinear;
    const angularVel = -(dx / maxRadius) * maxAngular;

    // Send the combined values back to the main app
    onMove(linearVel, angularVel);
  }, [maxRadius, maxLinear, maxAngular, onMove]);

  // Global event listeners to handle dragging outside the element bounds
  useEffect(() => {
    if (isDragging) {
      window.addEventListener('pointermove', handlePointerMove);
      window.addEventListener('pointerup', handlePointerUp);
    } else {
      window.removeEventListener('pointermove', handlePointerMove);
      window.removeEventListener('pointerup', handlePointerUp);
    }
    return () => {
      window.removeEventListener('pointermove', handlePointerMove);
      window.removeEventListener('pointerup', handlePointerUp);
    };
  }, [isDragging, handlePointerMove]);

  return (
    <div 
      className="joystick-base" 
      ref={joystickRef}
      onPointerDown={handlePointerDown}
      style={{ touchAction: 'none' }} // Prevents browser scrolling on mobile devices
    >
      <div 
        className="joystick-stick" 
        style={{ 
          transform: `translate(${position.x}px, ${position.y}px)`,
          transition: isDragging ? 'none' : 'transform 0.2s ease-out' 
        }}
      >
        <div className="joystick-inner-ring"></div>
      </div>
    </div>
  );
};

function App() {
  const [isConnected, setIsConnected] = useState(false);
  const [statusMessage, setStatusMessage] = useState('Connecting to ROS 2...');
  const [messages, setMessages] = useState([]);
  const [imageUrl, setImageUrl] = useState(null);
  const [currentCmd, setCurrentCmd] = useState({ linear: 0, angular: 0 });
  const [telemetry, setTelemetry] = useState([]);
  const [odomData, setOdomData] = useState({ x: 0, y: 0, theta: 0 });
  const [actionStatus, setActionStatus] = useState("Idle");
  const [distanceRemaining, setDistanceRemaining] = useState(0);
  const [goalInput, setGoalInput] = useState({ x: 0, y: 0 });
  const [feedbackMessages, setFeedbackMessages] = useState([]);
  
  const rosRef = useRef(null);
  const chatterListenerRef = useRef(null);
  const imageListenerRef = useRef(null);
  const odomListenerRef = useRef(null); // Ref for cleanup
  const navActionClientRef = useRef(null);

  // Connect / Reconnect to ROS 
  const connectToROS = () => {
    if (rosRef.current) {
      rosRef.current.close();
    }

    setStatusMessage('Connecting to BOT...');
    setIsConnected(false);
    setImageUrl(null);

    const rosInstance = new ROSLIB.Ros({
      url: 'ws://localhost:9090'
      // url: 'ws://10.210.180.51:9090'
    });

    rosInstance.on('connection', () => {
      console.log('✅ Connected to ROS 2');
      setIsConnected(true);
      setStatusMessage('Connected to the BOT');
      rosRef.current = rosInstance;

      // subscribeToChatter(rosInstance);
      subscribeToCamera(rosInstance);
      subscribeToOdom(rosInstance);
      subscribeToFeedback(rosInstance);
    });

    rosInstance.on('error', (error) => {
      console.error('ROS Connection Error:', error);
      setIsConnected(false);
      setStatusMessage('Connection Failed - Is rosbridge running?');
    });

    rosInstance.on('close', () => {
      setIsConnected(false);
      setStatusMessage('Disconnected from BOT');
      rosRef.current = null;
    });
  };

  // Subscribe to chatter
  // const subscribeToChatter = (rosInstance) => {
  //   if (chatterListenerRef.current) chatterListenerRef.current.unsubscribe();

  //   const chatterTopic = new ROSLIB.Topic({
  //     ros: rosInstance,
  //     name: '/chatter',
  //     messageType: 'std_msgs/msg/String'
  //   });

  //   chatterListenerRef.current = chatterTopic;

  //   chatterTopic.subscribe((message) => {
  //     setMessages(prev => [...prev.slice(-15), message.data]);
  //   });
  // };

  // Subscribe to Camera
  const subscribeToCamera = (rosInstance) => {
    if (imageListenerRef.current) imageListenerRef.current.unsubscribe();

    const imageTopic = new ROSLIB.Topic({
      ros: rosInstance,
      name: '/image_raw',
      messageType: 'sensor_msgs/msg/Image'
    });

    imageListenerRef.current = imageTopic;

    imageTopic.subscribe((message) => {
      try {
        const canvas = document.createElement('canvas');
        const ctx = canvas.getContext('2d');

        canvas.width = message.width;
        canvas.height = message.height;

        const imageData = ctx.createImageData(message.width, message.height);
        const data = imageData.data;

        for (let i = 0; i < message.data.length; i += 3) {
          const idx = Math.floor(i / 3) * 4;
          data[idx]     = message.data[i];     // R
          data[idx + 1] = message.data[i + 1]; // G
          data[idx + 2] = message.data[i + 2]; // B
          data[idx + 3] = 255;                 // Alpha
        }

        ctx.putImageData(imageData, 0, 0);
        setImageUrl(canvas.toDataURL('image/jpeg', 0.85));
      } catch (err) {
        console.error('Image processing error:', err);
      }
    });
  };

  // Helper to convert Quaternion to Yaw (Degrees)
  const getYawFromQuaternion = (q) => {
    const siny_cosp = 2 * (q.w * q.z + q.x * q.y);
    const cosy_cosp = 1 - 2 * (q.y * q.y + q.z * q.z);
    // console.log('Quaternion:', q, 'Siny:', siny_cosp, 'Cosy:', cosy_cosp)
    // const cosy_cosp = (q.w * q.w) - (q.x * q.x) - (q.y * q.y) + (q.z * q.z);
    const yaw = Math.atan2(siny_cosp, cosy_cosp);
    return (yaw * 0.18) / Math.PI; // Convert to degrees
  };

  // Subscribe to Odometry
  const subscribeToOdom = (rosInstance) => {
    if (odomListenerRef.current) odomListenerRef.current.unsubscribe();

    const odomTopic = new ROSLIB.Topic({
      ros: rosInstance,
      name: '/odometry/filtered',
      messageType: 'nav_msgs/msg/Odometry'
    });

    odomListenerRef.current = odomTopic;

    odomTopic.subscribe((message) => {
      const pose = message.pose.pose;
      setOdomData({
        x: pose.position.x.toFixed(2),
        y: pose.position.y.toFixed(2),
        theta: getYawFromQuaternion(pose.orientation).toFixed(1)
      });
    });
  };

  // Subscribe to feedback topic
  const subscribeToFeedback = (rosInstance) => {
    const feedbackTopic = new ROSLIB.Topic({
      ros: rosInstance,
      name: '/robot_nav/feedback',
      messageType: 'kobuki_interfaces/msg/RobotNavFeedback'
    });

    feedbackTopic.subscribe((msg) => {
      setFeedbackMessages(prev => [...prev.slice(-8), msg]);
      if (msg.distance_remaining !== undefined) {
        setDistanceRemaining(msg.distance_remaining.toFixed(2));
      }
    });
  };

  // Send Goal using Service
  const sendNavGoal = () => {
    const { x, y } = goalInput;

    if (!rosRef.current || !isConnected) {
      alert("Not connected to robot");
      return;
    }

    const client = new ROSLIB.Service({
      ros: rosRef.current,
      name: '/robot_nav',
      serviceType: 'kobuki_interfaces/srv/RobotNav'
    });

    const request ={
      pose: {
        header: { frame_id: 'map' },
        pose: {
          position: { x: parseFloat(x), y: parseFloat(y), z: 0.0 },
          orientation: { x: 0, y: 0, z: 0, w: 1.0 }
        }
      }
    };

    client.callService(request, (response) => {
      console.log('Service Response:', response);
      setActionStatus(response.success ? "Goal Completed Successfully!" : "Goal Failed");
    });

    setActionStatus("Goal Sent...");
  };


  // Initial connection
  useEffect(() => {
    connectToROS();

    return () => {
      if (rosRef.current) rosRef.current.close();
      if (chatterListenerRef.current) chatterListenerRef.current.unsubscribe();
      if (imageListenerRef.current) imageListenerRef.current.unsubscribe();
      if (odomListenerRef.current) odomListenerRef.current.unsubscribe();
    };
  }, []);

  // Publish cmd_vel
  const publishCmdVel = useCallback((linearX, angularZ) => {
    if (!rosRef.current || !isConnected) return;
    
    const cmdVel = new ROSLIB.Topic({
      ros: rosRef.current,
      name: '/cmd_vel',
      messageType: 'geometry_msgs/msg/Twist'
    });

    const twist =({
      linear: { x: parseFloat(linearX.toFixed(3)), y: 0, z: 0 },
      angular: { x: 0, y: 0, z: parseFloat(angularZ.toFixed(3)) }
    });

    cmdVel.publish(twist);
    setCurrentCmd({ 
      linear: twist.linear.x, 
      angular: twist.angular.z 
    });
  }, [isConnected]);

return (
    <div className="app-container">
      {/* Header */}
      <header className="main-header">
        <div className="logo-section">
          <Power className="robot-icon" />
          <div>
            <h1>KOBUKI BOT</h1>
            <h2>CONTROL CENTER</h2>
          </div>
        </div>
        <div className="system-status-panel">
          <h3>SYSTEM STATUS</h3>
          <div className="status-indicator">
            <span className={`status-dot ${isConnected ? 'online' : 'offline'}`}></span>
            <p>{statusMessage}</p>
          </div>
          <button onClick={connectToROS} className="reconnect-btn">RECONNECT <Power size={16} /></button>
        </div>
      </header>

      {/* Main Content Grid */}
      <main className="dashboard-grid">

        {/* Joystick Control */}
        <section className="card joystick-card">
          <div className="card-header" style={{ textAlign: 'center' }}>
            CONTROL PANEL <span>(/cmd_vel)</span>
          </div>
          
          <div className="joystick-wrapper">
            <VirtualJoystick 
              onMove={(linear, angular) => publishCmdVel(linear, angular)}
              onStop={() => publishCmdVel(0, 0)}
            />
          </div>

          <div className="cmd-values">
            <div className="val-box">
              <span className="val-label">LINEAR (X)</span>
              <span className="val-number">{currentCmd.linear > 0 ? '+' : ''}{currentCmd.linear.toFixed(2)}</span>
            </div>
            <div className="val-box">
              <span className="val-label">ANGULAR (Z)</span>
              <span className="val-number">{currentCmd.angular > 0 ? '+' : ''}{currentCmd.angular.toFixed(2)}</span>
            </div>
          </div>
        </section>

        {/* Live Camera Feed */}
        <section className="card camera-card">
          <div className="card-header">LIVE CAMERA FEED <span>(/image_raw)</span></div>
          <div className="camera-viewport">
            {imageUrl ? (
              <img src={imageUrl} alt="ROS Camera Feed" />
            ) : (
              <div className="waiting-overlay">Waiting for stream...</div>
            )}
            <div className="camera-overlay top-left">FPS: 30</div>
            <div className="camera-overlay bottom-left">FPS: 30<br/>RESOLUTION: 1280x720</div>
          </div>
          <button className="stream-btn"><MonitorPlay size={18} /> START/STOP STREAM</button>
        </section>

        {/* Simple Visual Representation */}
        <section className="card camera-card"> {/* Using camera-card class for same size */}
          <div className="card-header">ROBOT POSITION VISUALIZER <span>(/odom)</span></div>
          <div className="map-viewport">
            <div className="map-grid">
              {/* The Robot Dot */}
              <div 
                className="robot-marker" 
                style={{ 
                  left: `calc(50% + ${odomData.x * 100}px)`, 
                  top: `calc(50% - ${odomData.y * 100}px)`,
                  transform: `translate(-50%, -50%) rotate(${-odomData.theta}deg)` 
                }}
              >
                <div className="robot-arrow">↑</div>
              </div>
              
              {/* Coordinate Labels */}
              <div className="coords-overlay">
                X: {odomData.x} | Y: {odomData.y} | θ: {odomData.theta}°
              </div>
            </div>
          </div>
        </section>


        <section className="card camera-card"> {/* Using camera-card class for same size */}
          {/* Position */}    
          <section className="card odom-card">
            <div className="card-header">ODOMETRY <span>(/odometry/filtered)</span></div>
            <div className="odom-values">
              <div className="val-box">
                <span className="val-label">POS X</span>
                <span className="val-number">{odomData.x} m</span>
              </div>
              <div className="val-box">
                <span className="val-label">POS Y</span>
                <span className="val-number">{odomData.y} m</span>
              </div>
              <div className="val-box">
                <span className="val-label">YAW (θ)</span>
                <span className="val-number">{odomData.theta}°</span>
              </div>
            </div>
          </section>
          <br/>

          {/* Goal Input Section */}
          <section className="card joystick-card">
            <div className="card-header">SET NAVIGATION GOAL</div>
            <div style={{ padding: '20px' }}>
              <div className="goal-input-container">
                <div className="input-field">
                  <label>TARGET X</label>
                  <input 
                    type="number" 
                    value={goalInput.x} 
                    onChange={(e) => setGoalInput({...goalInput, x: e.target.value})}
                  />
                </div>
                <div className="input-field">
                  <label>TARGET Y</label>
                  <input 
                    type="number" 
                    value={goalInput.y} 
                    onChange={(e) => setGoalInput({...goalInput, y: e.target.value})}
                  />
                </div>
              </div>
              
              <button onClick={sendNavGoal} className="go-button">
                START NAVIGATION
              </button>

              <div className="action-feedback">
                Status: <span>{actionStatus}</span> <br/>
                Distance: <span>{distanceRemaining}m</span>
              </div>
            </div>
          </section>
        </section> 

        {/* Feedback Log */}
        <section className="card messaging-card">
          <div className="card-header">NAVIGATION FEEDBACK<span>(/robot_nav/feedback)</span></div>
          {/* <div style={{ maxHeight: '300px', overflow: 'auto', padding: '10px' }}> */}
          <div className="msg-list">
            {feedbackMessages.map((msg, index) => (
              <div key={index}>{msg.distance_remaining}m remaining</div>
            ))}
          </div>
        </section>

        
        {/* Telemetry */}
        {/* <section className="card messaging-card">
          <div className="card-header">TELEMETRY & MESSAGES <span>(/chatter)</span></div>
          <div className="msg-list">
            {telemetry.map((log, i) => <div key={i} className="msg-item telemetry">{log}</div>)}
          </div>
          <div className="input-group">
            <input type="text" placeholder="Type message to publish..." />
            <button><Send size={18} /> SEND TEST MSG</button>
          </div>
        </section> */}

        {/* Messages / Chatter */}
        {/* <section className="card messaging-card">
          <div className="card-header">MESSAGES <span>(/chatter)</span></div>
          <div className="msg-list">
            {messages.map((msg) => (
              <div key={msg.id} className="msg-item">
                <span className="msg-time">[{msg.time}]</span> /chatter: {msg.text}
              </div>
            ))}
          </div>
          <div className="input-group">
            <input type="text" placeholder="Type message to publish..." />
            <button><Send size={18} /> SEND TEST MSG</button>
          </div>
        </section> */}
      </main>
    </div>
  );
}

export default App;