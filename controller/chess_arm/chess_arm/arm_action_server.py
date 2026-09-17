import time

import rclpy
from rclpy.node import Node
from rclpy.action import ActionServer

from chess_interfaces.action import MovePiece


class ArmActionServer(Node):

    def __init__(self):
        super().__init__("arm_action_server")

        #provide move piece action
        self._action_server = ActionServer(
            self,
            MovePiece,
            "move_piece",
            self.execute_callback,
        )

        self.get_logger().info("MovePiece Action Server Ready")

    def execute_callback(self, goal_handle):

        self.get_logger().info(
            f"Received goal: {goal_handle.request.from_square} -> {goal_handle.request.to_square}"
        )

        feedback = MovePiece.Feedback()

        steps = [
            f"Moving above {goal_handle.request.from_square}",
            "Closing gripper",
            "Lifting piece",
            f"Moving above {goal_handle.request.to_square}",
            "Opening gripper",
        ]

        for step in steps:
            feedback.current_step = step
            goal_handle.publish_feedback(feedback)

            self.get_logger().info(step)

            time.sleep(1)

        goal_handle.succeed()

        result = MovePiece.Result()
        result.success = True
        result.message = "Piece moved successfully."

        return result


def main(args=None):
    rclpy.init(args=args)

    node = ArmActionServer()

    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass

    node.destroy_node()
    rclpy.shutdown()


if __name__ == "__main__":
    main()