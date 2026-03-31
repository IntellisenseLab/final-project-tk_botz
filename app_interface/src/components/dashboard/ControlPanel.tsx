import { useCallback, useRef, useEffect } from 'react';
import PanelHeader from './PanelHeader';
import { Gamepad2, ArrowUp, ArrowDown, ArrowLeft, ArrowRight, Square } from 'lucide-react';

interface ControlPanelProps {
  onVelocity: (linear: number, angular: number) => void;
  connected: boolean;
  linearVel: number;
  angularVel: number;
}

const ControlPanel = ({ onVelocity, connected, linearVel, angularVel }: ControlPanelProps) => {
  const intervalRef = useRef<number | null>(null);
  const activeRef = useRef<{ linear: number; angular: number }>({ linear: 0, angular: 0 });

  const startPublishing = useCallback((linear: number, angular: number) => {
    if (!connected) return;
    activeRef.current = { linear, angular };
    onVelocity(linear, angular);
    if (intervalRef.current) clearInterval(intervalRef.current);
    intervalRef.current = window.setInterval(() => {
      onVelocity(activeRef.current.linear, activeRef.current.angular);
    }, 100);
  }, [connected, onVelocity]);

  const stopPublishing = useCallback(() => {
    if (intervalRef.current) {
      clearInterval(intervalRef.current);
      intervalRef.current = null;
    }
    activeRef.current = { linear: 0, angular: 0 };
    onVelocity(0, 0);
  }, [onVelocity]);

  useEffect(() => {
    const handleKey = (e: KeyboardEvent) => {
      if (!connected) return;
      const speed = 0.3;
      const turnSpeed = 0.5;
      switch (e.key) {
        case 'w': case 'ArrowUp': startPublishing(speed, 0); break;
        case 's': case 'ArrowDown': startPublishing(-speed, 0); break;
        case 'a': case 'ArrowLeft': startPublishing(0, turnSpeed); break;
        case 'd': case 'ArrowRight': startPublishing(0, -turnSpeed); break;
      }
    };
    const handleKeyUp = () => stopPublishing();

    window.addEventListener('keydown', handleKey);
    window.addEventListener('keyup', handleKeyUp);
    return () => {
      window.removeEventListener('keydown', handleKey);
      window.removeEventListener('keyup', handleKeyUp);
      if (intervalRef.current) clearInterval(intervalRef.current);
    };
  }, [connected, startPublishing, stopPublishing]);

  const btnClass = `flex items-center justify-center w-12 h-12 rounded-md border border-border
    bg-secondary hover:bg-primary/20 active:bg-primary/40 transition-colors
    text-foreground disabled:opacity-30 disabled:cursor-not-allowed`;

  return (
    <div className="flex flex-col rounded-lg border border-border bg-card overflow-hidden">
      <PanelHeader
        title="Manual Control"
        icon={<Gamepad2 className="w-4 h-4 text-primary" />}
        status={connected ? 'active' : 'inactive'}
      >
        <span className="text-xs font-mono text-muted-foreground">WASD / Arrows</span>
      </PanelHeader>
      <div className="p-4 flex flex-col items-center gap-3">
        {/* D-pad */}
        <div className="grid grid-cols-3 gap-1">
          <div />
          <button
            className={btnClass}
            disabled={!connected}
            onMouseDown={() => startPublishing(0.3, 0)}
            onMouseUp={stopPublishing}
            onMouseLeave={stopPublishing}
          >
            <ArrowUp className="w-5 h-5" />
          </button>
          <div />
          <button
            className={btnClass}
            disabled={!connected}
            onMouseDown={() => startPublishing(0, 0.5)}
            onMouseUp={stopPublishing}
            onMouseLeave={stopPublishing}
          >
            <ArrowLeft className="w-5 h-5" />
          </button>
          <button
            className={`${btnClass} bg-destructive/20 hover:bg-destructive/40`}
            disabled={!connected}
            onClick={stopPublishing}
          >
            <Square className="w-4 h-4" />
          </button>
          <button
            className={btnClass}
            disabled={!connected}
            onMouseDown={() => startPublishing(0, -0.5)}
            onMouseUp={stopPublishing}
            onMouseLeave={stopPublishing}
          >
            <ArrowRight className="w-5 h-5" />
          </button>
          <div />
          <button
            className={btnClass}
            disabled={!connected}
            onMouseDown={() => startPublishing(-0.3, 0)}
            onMouseUp={stopPublishing}
            onMouseLeave={stopPublishing}
          >
            <ArrowDown className="w-5 h-5" />
          </button>
          <div />
        </div>

        {/* Velocity readout */}
        <div className="w-full grid grid-cols-2 gap-2 text-xs font-mono">
          <div className="flex flex-col items-center p-2 rounded bg-secondary/50 border border-border">
            <span className="text-muted-foreground">LIN VEL</span>
            <span className="text-primary text-lg font-bold">{linearVel.toFixed(2)}</span>
            <span className="text-muted-foreground">m/s</span>
          </div>
          <div className="flex flex-col items-center p-2 rounded bg-secondary/50 border border-border">
            <span className="text-muted-foreground">ANG VEL</span>
            <span className="text-primary text-lg font-bold">{angularVel.toFixed(2)}</span>
            <span className="text-muted-foreground">rad/s</span>
          </div>
        </div>
      </div>
    </div>
  );
};

export default ControlPanel;
