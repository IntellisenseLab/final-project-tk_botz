import PanelHeader from './PanelHeader';
import { Activity, Wifi, WifiOff, Navigation, AlertTriangle, CheckCircle2, Loader2 } from 'lucide-react';
import type { RobotState, RobotPose, NavigationFeedback } from '@/hooks/useROS';

interface StatusPanelProps {
  connected: boolean;
  robotState: RobotState;
  pose: RobotPose;
  navFeedback: NavigationFeedback;
  rosbridgeUrl: string;
  onUrlChange: (url: string) => void;
  onConnect: () => void;
  onDisconnect: () => void;
}

const stateConfig: Record<RobotState, { label: string; color: string; icon: React.ReactNode }> = {
  disconnected: { label: 'DISCONNECTED', color: 'text-muted-foreground', icon: <WifiOff className="w-4 h-4" /> },
  idle: { label: 'IDLE', color: 'text-accent', icon: <CheckCircle2 className="w-4 h-4" /> },
  moving: { label: 'MOVING', color: 'text-primary', icon: <Loader2 className="w-4 h-4 animate-spin" /> },
  goal_reached: { label: 'GOAL REACHED', color: 'text-accent', icon: <Navigation className="w-4 h-4" /> },
  error: { label: 'ERROR', color: 'text-destructive', icon: <AlertTriangle className="w-4 h-4" /> },
};

const StatusPanel = ({
  connected,
  robotState,
  pose,
  navFeedback,
  rosbridgeUrl,
  onUrlChange,
  onConnect,
  onDisconnect,
}: StatusPanelProps) => {
  const state = stateConfig[robotState];

  return (
    <div className="flex flex-col rounded-lg border border-border bg-card overflow-hidden">
      <PanelHeader
        title="System Status"
        icon={<Activity className="w-4 h-4 text-primary" />}
        status={connected ? 'active' : 'inactive'}
      />
      <div className="p-4 space-y-4 text-xs font-mono">
        {/* Connection */}
        <div className="space-y-2">
          <label className="text-muted-foreground uppercase tracking-wider">Rosbridge</label>
          <div className="flex gap-2">
            <input
              className="flex-1 px-2 py-1.5 rounded bg-secondary border border-border text-foreground text-xs font-mono focus:outline-none focus:ring-1 focus:ring-primary"
              value={rosbridgeUrl}
              onChange={(e) => onUrlChange(e.target.value)}
              placeholder="ws://localhost:9090"
            />
            <button
              onClick={connected ? onDisconnect : onConnect}
              className={`px-3 py-1.5 rounded border font-semibold uppercase tracking-wider transition-colors ${
                connected
                  ? 'border-destructive text-destructive hover:bg-destructive/20'
                  : 'border-primary text-primary hover:bg-primary/20'
              }`}
            >
              {connected ? <WifiOff className="w-3.5 h-3.5" /> : <Wifi className="w-3.5 h-3.5" />}
            </button>
          </div>
        </div>

        {/* Robot state */}
        <div className="flex items-center gap-2 p-2 rounded bg-secondary/50 border border-border">
          <span className={state.color}>{state.icon}</span>
          <span className={`font-bold ${state.color}`}>{state.label}</span>
        </div>

        {/* Pose */}
        <div className="space-y-1">
          <span className="text-muted-foreground uppercase tracking-wider">Pose</span>
          <div className="grid grid-cols-3 gap-1">
            {[
              { label: 'X', value: pose.x.toFixed(3) },
              { label: 'Y', value: pose.y.toFixed(3) },
              { label: 'θ', value: `${(pose.theta * 180 / Math.PI).toFixed(1)}°` },
            ].map(({ label, value }) => (
              <div key={label} className="flex flex-col items-center p-1.5 rounded bg-secondary/50 border border-border">
                <span className="text-muted-foreground">{label}</span>
                <span className="text-primary font-bold">{value}</span>
              </div>
            ))}
          </div>
        </div>

        {/* Navigation feedback */}
        <div className="space-y-1">
          <span className="text-muted-foreground uppercase tracking-wider">Navigation</span>
          <div className="p-2 rounded bg-secondary/50 border border-border space-y-2">
            <div className="flex justify-between">
              <span className="text-muted-foreground">Status</span>
              <span className="text-foreground">{navFeedback.status}</span>
            </div>
            <div className="w-full bg-secondary rounded-full h-1.5">
              <div
                className="bg-primary h-1.5 rounded-full transition-all duration-300"
                style={{ width: `${navFeedback.progress}%` }}
              />
            </div>
            {navFeedback.message && (
              <p className="text-muted-foreground text-[10px]">{navFeedback.message}</p>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};

export default StatusPanel;
