import { useRef, useEffect, useCallback } from 'react';
import PanelHeader from './PanelHeader';
import { Map } from 'lucide-react';
import type { OccupancyGridData, RobotPose } from '@/hooks/useROS';

interface MapPanelProps {
  mapData: OccupancyGridData | null;
  pose: RobotPose;
  onGoalSet?: (x: number, y: number) => void;
  connected: boolean;
}

const MapPanel = ({ mapData, pose, onGoalSet, connected }: MapPanelProps) => {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const containerRef = useRef<HTMLDivElement>(null);

  const drawMap = useCallback(() => {
    const canvas = canvasRef.current;
    const container = containerRef.current;
    if (!canvas || !container) return;

    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    const w = container.clientWidth;
    const h = container.clientHeight;
    canvas.width = w;
    canvas.height = h;

    // Background grid
    ctx.fillStyle = '#0d1117';
    ctx.fillRect(0, 0, w, h);

    // Draw grid lines
    ctx.strokeStyle = '#161b22';
    ctx.lineWidth = 1;
    for (let x = 0; x < w; x += 20) {
      ctx.beginPath();
      ctx.moveTo(x, 0);
      ctx.lineTo(x, h);
      ctx.stroke();
    }
    for (let y = 0; y < h; y += 20) {
      ctx.beginPath();
      ctx.moveTo(0, y);
      ctx.lineTo(w, y);
      ctx.stroke();
    }

    if (mapData) {
      const scale = Math.min(w / (mapData.width * mapData.resolution), h / (mapData.height * mapData.resolution));
      const offsetX = (w - mapData.width * mapData.resolution * scale) / 2;
      const offsetY = (h - mapData.height * mapData.resolution * scale) / 2;

      const cellW = (mapData.resolution * scale);
      const cellH = (mapData.resolution * scale);

      for (let row = 0; row < mapData.height; row++) {
        for (let col = 0; col < mapData.width; col++) {
          const val = mapData.data[row * mapData.width + col];
          if (val === -1) continue; // unknown
          
          const px = offsetX + col * cellW;
          const py = offsetY + (mapData.height - 1 - row) * cellH;
          
          if (val > 50) {
            ctx.fillStyle = '#00e5ff';
            ctx.globalAlpha = 0.8;
          } else if (val === 0) {
            ctx.fillStyle = '#1a2332';
            ctx.globalAlpha = 0.6;
          } else {
            ctx.fillStyle = '#2d4a3e';
            ctx.globalAlpha = 0.4;
          }
          ctx.fillRect(px, py, Math.max(cellW, 1), Math.max(cellH, 1));
          ctx.globalAlpha = 1;
        }
      }

      // Draw robot
      const robotX = offsetX + (pose.x - mapData.origin.x) / mapData.resolution * cellW;
      const robotY = offsetY + (mapData.height - (pose.y - mapData.origin.y) / mapData.resolution) * cellH;

      ctx.save();
      ctx.translate(robotX, robotY);
      ctx.rotate(-pose.theta);

      // Robot body
      ctx.fillStyle = '#00e5ff';
      ctx.shadowColor = '#00e5ff';
      ctx.shadowBlur = 15;
      ctx.beginPath();
      ctx.moveTo(10, 0);
      ctx.lineTo(-6, 7);
      ctx.lineTo(-6, -7);
      ctx.closePath();
      ctx.fill();
      ctx.shadowBlur = 0;

      ctx.restore();
    } else {
      // Demo: draw robot at center when no map
      const cx = w / 2;
      const cy = h / 2;

      ctx.save();
      ctx.translate(cx, cy);
      ctx.rotate(-pose.theta);

      ctx.fillStyle = '#00e5ff';
      ctx.shadowColor = '#00e5ff';
      ctx.shadowBlur = 20;
      ctx.beginPath();
      ctx.moveTo(16, 0);
      ctx.lineTo(-10, 10);
      ctx.lineTo(-10, -10);
      ctx.closePath();
      ctx.fill();
      ctx.shadowBlur = 0;
      ctx.restore();

      // Coordinate text
      ctx.fillStyle = '#8b949e';
      ctx.font = '11px JetBrains Mono';
      ctx.fillText(`x: ${pose.x.toFixed(3)}  y: ${pose.y.toFixed(3)}  θ: ${(pose.theta * 180 / Math.PI).toFixed(1)}°`, 10, h - 10);

      // "No map data" notice
      ctx.fillStyle = '#484f58';
      ctx.font = '12px JetBrains Mono';
      ctx.textAlign = 'center';
      ctx.fillText(connected ? 'Waiting for map data...' : 'Not connected', cx, cy + 40);
      ctx.textAlign = 'start';
    }
  }, [mapData, pose, connected]);

  useEffect(() => {
    drawMap();
    const observer = new ResizeObserver(drawMap);
    if (containerRef.current) observer.observe(containerRef.current);
    return () => observer.disconnect();
  }, [drawMap]);

  const handleClick = (e: React.MouseEvent<HTMLCanvasElement>) => {
    if (!mapData || !onGoalSet) return;
    const canvas = canvasRef.current;
    if (!canvas) return;

    const rect = canvas.getBoundingClientRect();
    const clickX = e.clientX - rect.left;
    const clickY = e.clientY - rect.top;

    const scale = Math.min(canvas.width / (mapData.width * mapData.resolution), canvas.height / (mapData.height * mapData.resolution));
    const offsetX = (canvas.width - mapData.width * mapData.resolution * scale) / 2;
    const offsetY = (canvas.height - mapData.height * mapData.resolution * scale) / 2;

    const mapX = (clickX - offsetX) / scale * mapData.resolution + mapData.origin.x;
    const mapY = (mapData.height * mapData.resolution - (clickY - offsetY) / scale * mapData.resolution) + mapData.origin.y;

    onGoalSet(mapX, mapY);
  };

  return (
    <div className="flex flex-col h-full rounded-lg border border-border bg-card overflow-hidden">
      <PanelHeader
        title="Map View"
        icon={<Map className="w-4 h-4 text-primary" />}
        status={connected ? (mapData ? 'active' : 'warning') : 'inactive'}
      />
      <div ref={containerRef} className="flex-1 relative cursor-crosshair">
        <canvas
          ref={canvasRef}
          className="w-full h-full"
          onClick={handleClick}
        />
        <div className="absolute top-2 right-2 scanline w-full h-full pointer-events-none" />
      </div>
    </div>
  );
};

export default MapPanel;
