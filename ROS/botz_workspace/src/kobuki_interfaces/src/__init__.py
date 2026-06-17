self._action_server = ActionServer(
    self,
    RobotNav,
    '/robot_nav',  # Ensure this matches exactly
    self.execute_callback
)
