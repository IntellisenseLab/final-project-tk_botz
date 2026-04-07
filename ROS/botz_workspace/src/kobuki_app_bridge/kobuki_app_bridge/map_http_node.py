import io
import threading

import numpy as np
from PIL import Image
from aiohttp import web

import rclpy
from rclpy.node import Node
from nav_msgs.msg import OccupancyGrid


class MapHttpNode(Node):
    def __init__(self):
        super().__init__("map_http_node")
        self.declare_parameter("map_topic", "/map")
        self.declare_parameter("http_host", "0.0.0.0")
        self.declare_parameter("http_port", 8080)

        map_topic = self.get_parameter("map_topic").get_parameter_value().string_value
        self.host = self.get_parameter("http_host").get_parameter_value().string_value
        self.port = int(self.get_parameter("http_port").value)

        self.latest_png = None
        self.lock = threading.Lock()

        self.create_subscription(OccupancyGrid, map_topic, self.on_map, 10)

        self.app = web.Application()
        self.app.router.add_get("/map", self.handle_map)
        self.runner = web.AppRunner(self.app)

        self.http_thread = threading.Thread(target=self.run_http_server, daemon=True)
        self.http_thread.start()

        self.get_logger().info(f"HTTP map server started at http://{self.host}:{self.port}/map")

    def on_map(self, msg: OccupancyGrid):
        w = msg.info.width
        h = msg.info.height
        arr = np.array(msg.data, dtype=np.int16).reshape((h, w))

        img = np.zeros((h, w), dtype=np.uint8)
        img[arr == -1] = 127
        img[arr == 0] = 255
        img[arr > 50] = 0
        img[(arr > 0) & (arr <= 50)] = 180

        img = np.flipud(img)

        pil = Image.fromarray(img, mode="L")
        buf = io.BytesIO()
        pil.save(buf, format="PNG")
        png_bytes = buf.getvalue()

        with self.lock:
            self.latest_png = png_bytes

    async def handle_map(self, request):
        with self.lock:
            data = self.latest_png

        if data is None:
            return web.json_response({"error": "map not available yet"}, status=503)

        return web.Response(body=data, content_type="image/png")

    def run_http_server(self):
        import asyncio

        async def _start():
            await self.runner.setup()
            site = web.TCPSite(self.runner, self.host, self.port)
            await site.start()
            while rclpy.ok():
                await asyncio.sleep(0.2)

        asyncio.run(_start())


def main(args=None):
    rclpy.init(args=args)
    node = MapHttpNode()
    try:
        rclpy.spin(node)
    finally:
        node.destroy_node()
        rclpy.shutdown()