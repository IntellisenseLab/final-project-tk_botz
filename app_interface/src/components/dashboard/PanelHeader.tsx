interface PanelHeaderProps {
  title: string;
  icon?: React.ReactNode;
  status?: 'active' | 'inactive' | 'warning';
  children?: React.ReactNode;
}

const PanelHeader = ({ title, icon, status, children }: PanelHeaderProps) => {
  const statusColor = {
    active: 'bg-accent',
    inactive: 'bg-muted-foreground',
    warning: 'bg-warning',
  };

  return (
    <div className="flex items-center justify-between px-4 py-2 border-b border-border bg-secondary/50">
      <div className="flex items-center gap-2">
        {status && (
          <span className={`w-2 h-2 rounded-full ${statusColor[status]} animate-pulse-glow`} />
        )}
        {icon}
        <h3 className="text-sm font-mono font-semibold uppercase tracking-wider text-foreground">
          {title}
        </h3>
      </div>
      {children}
    </div>
  );
};

export default PanelHeader;
