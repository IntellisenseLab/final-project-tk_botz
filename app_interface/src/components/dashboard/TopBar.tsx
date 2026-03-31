import { Bot, Cpu } from 'lucide-react';

interface TopBarProps {
  connected: boolean;
}

const TopBar = ({ connected }: TopBarProps) => {
  return (
    <header className="flex items-center justify-between px-6 py-3 border-b border-border bg-card/80 backdrop-blur-sm">
      <div className="flex items-center gap-3">
        <div className="relative">
          <Bot className="w-7 h-7 text-primary" />
          <span
            className={`absolute -bottom-0.5 -right-0.5 w-2.5 h-2.5 rounded-full border-2 border-card ${
              connected ? 'bg-accent' : 'bg-muted-foreground'
            }`}
          />
        </div>
        <div>
          <h1 className="text-base font-bold font-mono tracking-wider text-foreground">
            QBOT <span className="text-primary">CONTROL</span>
          </h1>
          <p className="text-[10px] font-mono text-muted-foreground tracking-widest uppercase">
            ROS 2 Mission Interface
          </p>
        </div>
      </div>
      <div className="flex items-center gap-4">
        <div className="flex items-center gap-2 px-3 py-1 rounded-md bg-secondary border border-border">
          <Cpu className="w-3.5 h-3.5 text-primary" />
          <span className="text-xs font-mono text-muted-foreground">
            {connected ? 'ONLINE' : 'OFFLINE'}
          </span>
        </div>
      </div>
    </header>
  );
};

export default TopBar;
