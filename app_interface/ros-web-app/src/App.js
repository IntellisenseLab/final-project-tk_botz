import React, { useEffect, useState, useRef } from 'react';
import * as ROSLIB from 'roslib';

function App() {
  const [isConnected, setIsConnected] = useState(false);
  const [statusMessage, setStatusMessage] = useState('Connecting to ROS 2...');
  const [messages, setMessages] = useState([]);
  const [imageUrl, setImageUrl] = useState(null);

  const rosRef = useRef(null);
  const chatterListenerRef = useRef(null);
  const imageListenerRef = useRef(null);

  // Connect / Reconnect to ROS
  const connectToROS = () => {
    if (rosRef.current) {
      rosRef.current.close();
    }

    setStatusMessage('Connecting to ROS 2...');
    setIsConnected(false);
    setImageUrl(null);

    const rosInstance = new ROSLIB.Ros({
      url: 'ws://localhost:9090'
    });

    rosInstance.on('connection', () => {
      console.log('✅ Connected to ROS 2');
      setIsConnected(true);
      setStatusMessage('Connected to ROS 2 Humble');
      rosRef.current = rosInstance;

      subscribeToChatter(rosInstance);
      subscribeToCamera(rosInstance);
    });

    rosInstance.on('error', (error) => {
      console.error('ROS Connection Error:', error);
      setIsConnected(false);
      setStatusMessage('Connection Failed - Is rosbridge running?');
    });

    rosInstance.on('close', () => {
      setIsConnected(false);
      setStatusMessage('Disconnected from ROS');
      rosRef.current = null;
    });
  };

  // Subscribe to chatter
  const subscribeToChatter = (rosInstance) => {
    if (chatterListenerRef.current) chatterListenerRef.current.unsubscribe();

    const chatterTopic = new ROSLIB.Topic({
      ros: rosInstance,
      name: '/chatter',
      messageType: 'std_msgs/msg/String'
    });

    chatterListenerRef.current = chatterTopic;

    chatterTopic.subscribe((message) => {
      setMessages(prev => [...prev.slice(-15), message.data]);
    });
  };

  // Subscribe to Camera
  const subscribeToCamera = (rosInstance) => {
    if (imageListenerRef.current) imageListenerRef.current.unsubscribe();

    const imageTopic = new ROSLIB.Topic({
      ros: rosInstance,
      name: '/image_raw',        // ← Change this to your actual camera topic
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

  // Initial connection
  useEffect(() => {
    connectToROS();

    return () => {
      if (rosRef.current) rosRef.current.close();
      if (chatterListenerRef.current) chatterListenerRef.current.unsubscribe();
      if (imageListenerRef.current) imageListenerRef.current.unsubscribe();
    };
  }, []);

  // Publish cmd_vel
  const publishCmdVel = (linearX, angularZ) => {
    if (!rosRef.current || !isConnected) {
      alert("Not connected to ROS!");
      return;
    }

    const cmdVel = new ROSLIB.Topic({
      ros: rosRef.current,
      name: '/cmd_vel',
      messageType: 'geometry_msgs/msg/Twist'
    });

    const twist = {
      linear: { x: linearX, y: 0, z: 0 },
      angular: { x: 0, y: 0, z: angularZ }
    };

    cmdVel.publish(twist);
  };

  return (
    <div style={{ padding: '30px', maxWidth: '1100px', margin: '0 auto', fontFamily: 'Arial, sans-serif' }}>
      <h1>ROS 2 Humble Web Interface</h1>

      {/* Connection Status */}
      <div style={{
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        padding: '15px 20px',
        backgroundColor: isConnected ? '#d4edda' : '#f8d7da',
        borderRadius: '10px',
        marginBottom: '25px',
        border: `2px solid ${isConnected ? '#28a745' : '#dc3545'}`
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
          <div style={{
            width: '18px',
            height: '18px',
            borderRadius: '50%',
            backgroundColor: isConnected ? '#28a745' : '#dc3545',
            boxShadow: isConnected ? '0 0 10px #28a745' : '0 0 10px #dc3545'
          }} />
          <strong style={{ fontSize: '18px' }}>{statusMessage}</strong>
        </div>

        <button 
          onClick={connectToROS}
          style={{
            padding: '8px 16px',
            backgroundColor: '#007bff',
            color: 'white',
            border: 'none',
            borderRadius: '6px',
            cursor: 'pointer'
          }}
        >
          Reconnect
        </button>
      </div>

      {/* Robot Control Section */}
      <div style={{ marginBottom: '40px', textAlign: 'center' }}>
        <h2>Robot Control</h2>
        <div style={joystickContainer}>
          
          {/* Row 1, Col 2: Forward */}
          <button 
            style={{ ...buttonStyle, gridColumn: '2', gridRow: '1' }} 
            onClick={() => publishCmdVel(0.4, 0)}
          >
            ↑
          </button>

          {/* Row 2, Col 1: Left */}
          <button 
            style={{ ...buttonStyle, gridColumn: '1', gridRow: '2' }} 
            onClick={() => publishCmdVel(0, 0.6)}
          >
            ↺
          </button>

          {/* Row 2, Col 2: Stop */}
          <button 
            style={{ ...buttonStyle, gridColumn: '2', gridRow: '2', backgroundColor: '#dc3545' }} 
            onClick={() => publishCmdVel(0, 0)}
          >
            STOP
          </button>

          {/* Row 2, Col 3: Right */}
          <button 
            style={{ ...buttonStyle, gridColumn: '3', gridRow: '2' }} 
            onClick={() => publishCmdVel(0, -0.6)}
          >
            ↻
          </button>

          {/* Row 3, Col 2: Backward */}
          <button 
            style={{ ...buttonStyle, gridColumn: '2', gridRow: '3' }} 
            onClick={() => publishCmdVel(-0.3, 0)}
          >
            ↓
          </button>

        </div>
      </div>

      {/* Camera Viewer */}
      <div style={{ marginBottom: '40px' }}>
        <h2>Camera Viewer</h2>
        <div style={{
          border: '2px solid #ddd',
          borderRadius: '10px',
          overflow: 'hidden',
          backgroundColor: '#000',
          minHeight: '400px',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center'
        }}>
          {imageUrl ? (
            <img 
              src={imageUrl} 
              alt="ROS Camera" 
              style={{ maxWidth: '100%', maxHeight: '600px' }} 
            />
          ) : (
            <div style={{ color: '#aaa', textAlign: 'center' }}>
              <p>Waiting for camera image...</p>
              <p style={{ fontSize: '14px' }}>
                Publish on topic: <strong>/image_raw</strong>
              </p>
            </div>
          )}
        </div>
      </div>

      {/* Messages Section */}
      <div>
        <h2>Messages from /chatter</h2>
        <div style={{
          backgroundColor: '#f8f9fa',
          border: '1px solid #ddd',
          borderRadius: '10px',
          padding: '15px',
          minHeight: '200px',
          maxHeight: '320px',
          overflowY: 'auto'
        }}>
          {messages.length === 0 ? (
            <p style={{ color: '#888', fontStyle: 'italic' }}>
              Run in another terminal: <strong>ros2 run demo_nodes_cpp talker</strong>
            </p>
          ) : (
            messages.map((msg, index) => (
              <div key={index} style={{
                padding: '8px 10px',
                margin: '4px 0',
                backgroundColor: 'white',
                borderRadius: '6px',
                borderLeft: '4px solid #007bff'
              }}>
                {msg}
              </div>
            ))
          )}
        </div>
      </div>
    </div>
  );
}

const joystickContainer = {
  display: 'grid',
  gridTemplateColumns: 'repeat(3, 100px)', // 3 columns
  gridTemplateRows: 'repeat(3, 100px)',    // 3 rows
  gap: '10px',
  justifyContent: 'center',
  alignItems: 'center',
  margin: '0 auto',
  maxWidth: '320px'
};

const buttonStyle = {
  width: '100%',
  height: '100%',
  fontSize: '18px',
  fontWeight: 'bold',
  border: 'none',
  borderRadius: '12px',
  backgroundColor: '#007bff',
  color: 'white',
  cursor: 'pointer',
  transition: 'background 0.2s',
};

export default App;