import PanelHeader from './PanelHeader';
import { Camera, VideoOff } from 'lucide-react';

interface CameraPanelProps {
  image: string | null;
  connected: boolean;
}

const CameraPanel = ({ image, connected }: CameraPanelProps) => {
  return (
    <div className="flex flex-col rounded-lg border border-border bg-card overflow-hidden">
      <PanelHeader
        title="Camera Feed"
        icon={<Camera className="w-4 h-4 text-primary" />}
        status={image ? 'active' : 'inactive'}
      />
      <div className="flex-1 flex items-center justify-center bg-secondary/30 min-h-[140px] relative">
        {image ? (
          <img src={image} alt="Camera feed" className="w-full h-full object-contain" />
        ) : (
          <div className="flex flex-col items-center gap-2 text-muted-foreground">
            <VideoOff className="w-8 h-8" />
            <span className="text-xs font-mono">
              {connected ? 'No camera feed' : 'Not connected'}
            </span>
          </div>
        )}
        {image && <div className="absolute top-2 right-2 w-2 h-2 rounded-full bg-destructive animate-pulse-glow" />}
      </div>
    </div>
  );
};

export default CameraPanel;
