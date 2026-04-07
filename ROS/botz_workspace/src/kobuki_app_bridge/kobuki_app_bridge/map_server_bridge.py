"""
map_server_bridge.py

Purpose:
- Subscribe to nav_msgs/OccupancyGrid map topic.
- Convert OccupancyGrid to grayscale PNG bytes.
- Save PNG to disk on every map update.
- Expose latest PNG through module-level shared buffer for in-process consumers.

Subscribes:
- /map (default, configurable): nav_msgs/OccupancyGrid

Publishes:
- None (state is exposed via module-level getter)
"""

import io
import threading
from typing import Optional

import numpy as np
from PIL import Image
import rclpy
from rclpy.node import Node
from nav_msgs.msg import OccupancyGrid


_SHARED_LOCK = threading.Lock()
_SHARED_MAP_PNG: Optional[bytes] = None


def set_latest_map_png(data: bytes) -> None:
    global _SHARED_MAP_PNG
    with _SHARED_LOCK:
        _SHARED_MAP_PNG = data


def get_latest_map_png() -> Optional[bytes]:
    with _SHARED_LOCK:
        return _SHARED_MAP_PNG


class MapServerBridge(Node):
    def __init__(self) -> None:
        super().__init__("map_server_bridge")

        self.declare_parameter("map_topic", "/map")
        self.declare_parameter("map_save_path", "/tmp/current_map.png")

        self.map_topic = str(self.get_parameter("map_topic").value)
        self.map_save_path = str(self.get_parameter("map_save_path").value)

        self.create_subscription(OccupancyGrid, self.map_topic, self._on_map, 10)

        self.get_logger().info(
            f"Map bridge started. topic={self.map_topic} save_path={self.map_save_path}"
        )

    def _on_map(self, msg: OccupancyGrid) -> None:
        try:
            width = int(msg.info.width)
            height = int(msg.info.height)
            if width <= 0 or height <= 0:
                self.get_logger().warn("Received map with invalid dimensions")
                return

            raw = np.array(msg.data, dtype=np.int16).reshape((height, width))

            # Map values to grayscale:
            # -1 unknown -> 128
            #  0 free    -> 255
            # 100 occ    -> 0
            image = np.full((height, width), 128, dtype=np.uint8)
            image[raw == 0] = 255
            image[raw >= 100] = 0

            # For intermediate occupancy values (1..99), interpolate toward black
            mask_mid = (raw > 0) & (raw < 100)
            image[mask_mid] = np.uint8(255 - (raw[mask_mid] * 255 // 100))

            # OccupancyGrid starts at bottom-left; image viewers assume top-left.
            image = np.flipud(image)

            pil_img = Image.fromarray(image, mode="L")
            byte_buf = io.BytesIO()
            pil_img.save(byte_buf, format="PNG")
            png_bytes = byte_buf.getvalue()

            set_latest_map_png(png_bytes)

            with open(self.map_save_path, "wb") as f:
                f.write(png_bytes)

            self.get_logger().info(
                f"Map updated and saved to {self.map_save_path} ({width}x{height})"
            )
        except Exception as exc:
            self.get_logger().error(f"Failed processing map: {exc}")


def main(args=None) -> None:
    rclpy.init(args=args)
    node = MapServerBridge()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()