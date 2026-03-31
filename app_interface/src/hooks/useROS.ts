import { useState, useEffect, useCallback, useRef } from 'react';
import { Ros, Topic, Service, ActionClient, Goal } from 'roslib';

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
  const cmdVelRef = useRef<Topic | null>(null);

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

      // cmd_vel publisher
      const cmdVel = new Topic({
        ros,
        name: '/cmd_vel',
        messageType: 'geometry_msgs/msg/Twist',
      });
      cmdVelRef.current = cmdVel;
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
    if (!cmdVelRef.current) return;
    cmdVelRef.current.publish({
      linear: { x: linear, y: 0, z: 0 },
      angular: { x: 0, y: 0, z: angular },
    });
  }, []);

  const sendNavigationGoal = useCallback((x: number, y: number, theta = 0) => {
    if (!rosRef.current || !connected) return;

    setRobotState('moving');
    setNavFeedback({ status: 'Navigating', progress: 0, message: `Goal: (${x.toFixed(2)}, ${y.toFixed(2)})` });

    const actionClient = new ActionClient({
      ros: rosRef.current,
      serverName: '/navigate',
      actionName: 'custom_interfaces/action/Navigation',
    });

    const goal = new Goal({
      actionClient,
      goalMessage: {
        target_x: x,
        target_y: y,
        target_theta: theta,
      },
    });

    goal.on('feedback', (feedback: any) => {
      setNavFeedback({
        status: 'Navigating',
        progress: feedback.progress || 0,
        message: feedback.status || 'In progress...',
      });
    });

    goal.on('result', (result: any) => {
      const success = result.success;
      setRobotState(success ? 'goal_reached' : 'error');
      setNavFeedback({
        status: success ? 'Goal Reached' : 'Failed',
        progress: success ? 100 : 0,
        message: result.message || (success ? 'Navigation complete' : 'Navigation failed'),
      });
      setTimeout(() => setRobotState('idle'), 3000);
    });

    goal.send();
  }, [connected]);

  const getLastPositions = useCallback(async (count: number): Promise<any[]> => {
    if (!rosRef.current || !connected) return [];

    return new Promise((resolve) => {
      const service = new Service({
        ros: rosRef.current!,
        name: '/get_last_positions',
        serviceType: 'custom_interfaces/srv/GetLastPositions',
      });

      service.callService({ count } as any, (result: any) => {
        resolve(result.positions || []);
      }, () => resolve([]));
    });
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
