import { useState, useEffect, useCallback, useRef } from 'react';
import { Ros, Topic } from 'roslib';

export type RobotState = 'disconnected' | 'idle' | 'moving' | 'goal_reached' | 'error';

export interface RobotPose {
  x: number;
  y: number;
  theta: number;
}

export interface NavigationFeedback {
  status: string;
  progress: number;
  message: string;
}

export interface OccupancyGridData {
  width: number;
  height: number;
  resolution: number;
  origin: { x: number; y: number };
  data: number[];
}

export function useROS(url = 'ws://localhost:9090') {
  const [connected, setConnected] = useState(false);
  const [robotState, setRobotState] = useState<RobotState>('disconnected');
  const [pose, setPose] = useState<RobotPose>({ x: 0, y: 0, theta: 0 });
  const [mapData, setMapData] = useState<OccupancyGridData | null>(null);
  const [navFeedback, setNavFeedback] = useState<NavigationFeedback>({ status: 'Idle', progress: 0, message: '' });
  const [cameraImage, setCameraImage] = useState<string | null>(null);
  const [linearVel, setLinearVel] = useState(0);
  const [angularVel, setAngularVel] = useState(0);

  const rosRef = useRef<Ros | null>(null);
  const appCommandRef = useRef<Topic | null>(null);
  const appGoalRef = useRef<Topic | null>(null);
  const restBaseUrl = useRef<string>('');

  const connect = useCallback(() => {
    if (rosRef.current) {
      rosRef.current.close();
    }

    const ros = new Ros({ url });
    rosRef.current = ros;

    ros.on('connection', () => {
      setConnected(true);
      setRobotState('idle');

      // Subscribe to odometry
      const odomTopic = new Topic({
        ros,
        name: '/odom',
        messageType: 'nav_msgs/msg/Odometry',
      });
      odomTopic.subscribe((msg: any) => {
        const p = msg.pose?.pose?.position;
        const q = msg.pose?.pose?.orientation;
        if (p && q) {
          const theta = 2 * Math.atan2(q.z, q.w);
          setPose({ x: p.x, y: p.y, theta });
        }
        const lin = msg.twist?.twist?.linear;
        const ang = msg.twist?.twist?.angular;
        if (lin) setLinearVel(Math.sqrt(lin.x * lin.x + lin.y * lin.y));
        if (ang) setAngularVel(Math.abs(ang.z));
      });

      // Subscribe to map
      const mapTopic = new Topic({
        ros,
        name: '/map',
        messageType: 'nav_msgs/msg/OccupancyGrid',
      });
      mapTopic.subscribe((msg: any) => {
        setMapData({
          width: msg.info.width,
          height: msg.info.height,
          resolution: msg.info.resolution,
          origin: { x: msg.info.origin.position.x, y: msg.info.origin.position.y },
          data: msg.data,
        });
      });

      // Subscribe to camera
      const cameraTopic = new Topic({
        ros,
        name: '/camera/image_raw/compressed',
        messageType: 'sensor_msgs/msg/CompressedImage',
      });
      cameraTopic.subscribe((msg: any) => {
        setCameraImage(`data:image/jpeg;base64,${msg.data}`);
      });

      // /app/command publisher (bridge protocol)
      const appCommand = new Topic({
        ros,
        name: '/app/command',
        messageType: 'std_msgs/msg/String',
      });
      appCommandRef.current = appCommand;

      // /app/goal publisher (bridge protocol for navigation)
      const appGoal = new Topic({
        ros,
        name: '/app/goal',
        messageType: 'geometry_msgs/msg/PoseStamped',
      });
      appGoalRef.current = appGoal;

      // Derive REST base URL from WebSocket URL (e.g., ws://localhost:9090 -> http://localhost:8080)
      const wsUrl = new URL(url);
      const restUrl = `http://${wsUrl.hostname}:8080`;
      restBaseUrl.current = restUrl;
    });

    ros.on('error', () => {
      setRobotState('error');
    });

    ros.on('close', () => {
      setConnected(false);
      setRobotState('disconnected');
    });
  }, [url]);

  const disconnect = useCallback(() => {
    rosRef.current?.close();
  }, []);

  const publishVelocity = useCallback((linear: number, angular: number) => {
    if (!appCommandRef.current) return;
    // Publish via /app/command bridge protocol (JSON string)
    appCommandRef.current.publish({
      data: JSON.stringify({
        type: 'velocity',
        linear,
        angular,
      }),
    });
  }, []);

  const sendNavigationGoal = useCallback((x: number, y: number, theta = 0) => {
    if (!appGoalRef.current || !connected) return;

    setRobotState('moving');
    setNavFeedback({ status: 'Navigating', progress: 0, message: `Goal: (${x.toFixed(2)}, ${y.toFixed(2)})` });

    // Publish goal via /app/goal bridge protocol (geometry_msgs/PoseStamped)
    appGoalRef.current.publish({
      header: {
        frame_id: 'map',
        stamp: { secs: Math.floor(Date.now() / 1000), nsecs: (Date.now() % 1000) * 1e6 },
      },
      pose: {
        position: { x, y, z: 0 },
        orientation: {
          x: 0,
          y: 0,
          z: Math.sin(theta / 2),
          w: Math.cos(theta / 2),
        },
      },
    });

    // Status feedback handled by /app/goal_status topic (if wired in frontend later)
    // For now, set optimistic state
    setTimeout(() => {
      setNavFeedback({ status: 'To Backend', progress: 50, message: 'Goal sent to navigation stack' });
    }, 500);

    setTimeout(() => setRobotState('idle'), 5000);
  }, [connected]);

  const getLastPositions = useCallback(async (count: number): Promise<any[]> => {
    if (!connected) return [];

    try {
      const restUrl = restBaseUrl.current;
      if (!restUrl) return [];
      
      const response = await fetch(`${restUrl}/last_positions?count=${count}`);
      if (!response.ok) return [];
      
      const data = await response.json();
      return data.positions || [];
    } catch (error) {
      console.warn('Failed to fetch last positions:', error);
      return [];
    }
  }, [connected]);

  useEffect(() => {
    return () => {
      rosRef.current?.close();
    };
  }, []);

  return {
    connected,
    robotState,
    pose,
    mapData,
    navFeedback,
    cameraImage,
    linearVel,
    angularVel,
    connect,
    disconnect,
    publishVelocity,
    sendNavigationGoal,
    getLastPositions,
  };
}
