import { useState } from 'react';
import TopBar from '@/components/dashboard/TopBar';
import MapPanel from '@/components/dashboard/MapPanel';
import ControlPanel from '@/components/dashboard/ControlPanel';
import StatusPanel from '@/components/dashboard/StatusPanel';
import CameraPanel from '@/components/dashboard/CameraPanel';
import { useROS } from '@/hooks/useROS';

const Index = () => {
  const [rosbridgeUrl, setRosbridgeUrl] = useState('ws://localhost:9090');
  const ros = useROS(rosbridgeUrl);

  return (
    <div className="flex flex-col h-screen bg-background overflow-hidden">
      <TopBar connected={ros.connected} />
      <div className="flex-1 grid grid-cols-1 lg:grid-cols-[1fr_320px] gap-3 p-3 overflow-hidden">
        {/* Left: Map */}
        <MapPanel
          mapData={ros.mapData}
          pose={ros.pose}
          onGoalSet={ros.sendNavigationGoal}
          connected={ros.connected}
        />

        {/* Right: Controls & Status */}
        <div className="flex flex-col gap-3 overflow-y-auto">
          <StatusPanel
            connected={ros.connected}
            robotState={ros.robotState}
            pose={ros.pose}
            navFeedback={ros.navFeedback}
            rosbridgeUrl={rosbridgeUrl}
            onUrlChange={setRosbridgeUrl}
            onConnect={ros.connect}
            onDisconnect={ros.disconnect}
          />
          <ControlPanel
            onVelocity={ros.publishVelocity}
            connected={ros.connected}
            linearVel={ros.linearVel}
            angularVel={ros.angularVel}
          />
          <CameraPanel
            image={ros.cameraImage}
            connected={ros.connected}
          />
        </div>
      </div>
    </div>
  );
};

export default Index;
