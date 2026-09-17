import rclpy
from rclpy.node import Node
from rclpy.action import ActionClient

from chess_interfaces.action import MovePiece


class ArmActionClient(Node):

    def __init__(self):
        super().__init__("arm_action_client")

        self._client = ActionClient(
            self,
            MovePiece,
            "move_piece"
        )

    def send_goal(self):

        self._client.wait_for_server()

        goal = MovePiece.Goal()
        goal.from_square = "e2"
        goal.to_square = "e4"

        self.get_logger().info(
            f"Sending goal: {goal.from_square} -> {goal.to_square}"
        )

        future = self._client.send_goal_async(
            goal,
            feedback_callback=self.feedback_callback
        )

        future.add_done_callback(self.goal_response_callback)

    def goal_response_callback(self, future):

        goal_handle = future.result()

        if not goal_handle.accepted:
            self.get_logger().info("Goal rejected")
            return

        self.get_logger().info("Goal accepted")

        result_future = goal_handle.get_result_async()
        result_future.add_done_callback(self.result_callback)

    def feedback_callback(self, feedback_msg):

        feedback = feedback_msg.feedback

        self.get_logger().info(
            f"Feedback: {feedback.current_step}"
        )

    def result_callback(self, future):

        result = future.result().result

        self.get_logger().info(
            f"Success: {result.success}"
        )

        self.get_logger().info(
            result.message
        )

        rclpy.shutdown()


def main(args=None):

    rclpy.init(args=args)

    node = ArmActionClient()

    node.send_goal()

    rclpy.spin(node)


if __name__ == "__main__":
    main()