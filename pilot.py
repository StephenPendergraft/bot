"""Autonomous control client that solves IEEE Hardware Competition 2014."""

import sys
import lib.lib as lib
import client.ctrl_client as ctrl_client_mod
import client.sub_client as sub_client_mod


class Pilot:
    """Autonomous control client based on comprehensive state machine."""

    State = lib.Enum(('START', 'SMART_JERK', 'FIND_LINE', 'OSCILLATE',
                      'FOLLOW', 'CENTER_ON_X', 'ROTATE_ON_X',
                      'CENTER_ON_BLUE', 'AIM', 'FIRE',
                      'CHOOSE_DIR_BLUE', 'TURN_BACK',
                      'CENTER_ON_RED', 'FINISH', 'FOLLOW_ON_X'))

    def __init__(self, ctrl_addr="tcp://127.0.0.1:60000",
                 sub_addr="tcp://127.0.0.1:60001"):
        # Get config, build logger
        self.config = lib.get_config()
        self.logger = lib.get_logger()
        
        # Build control client
        try:
            self.ctrl_client = ctrl_client_mod.CtrlClient(ctrl_addr)
        except Exception, e:
            self.logger.error("Couldn't build CtrlClient; ctrl_addr: {},"
                              " error: {}".format(ctrl_addr, e))
            sys.exit(-1)

        # Build sub client
        try:
            self.sub_client = sub_client_mod.SubClient(sub_addr)
        except Exception, e:
            self.logger.error("Couldn't build SubClient; sub_addr: {},"
                              " error: {}".format(sub_addr, e))
            sys.exit(-1)

        # Initialize other members
        self.state = self.State.START
        self.blue_blocks = 0  # no. of blue blocks found and centered on
        self.darts_fired = 0  # no. of darts fired

    def __str__(self):
        return "[{}] blue_blocks: {}, darts_fired: {}".format(
            self.State.toString(self.state), self.blue_blocks,
            self.darts_fired)

    def run(self):
        self.logger.info("Starting attack run")
        # Start indefinite loop to run through states till FINISH
        last_state = None  # to detect state changes, mainly for debugging
        while self.state != self.State.FINISH:
            if self.state != last_state:
                self.logger.info(str(self))
                last_state = self.state

            if self.state == self.State.START:
                self.logger.info("Waiting for start")
                result = self.call('color_sensor', 'watch_for_color',
                    {"color": "green"})
                if result == True:
                    self.logger.info("Start signal found")
                    self.state = self.State.SMART_JERK
            elif self.state == self.State.SMART_JERK:
                self.call('follower', 'smart_jerk')
                self.call('follower', 'assign_states')
                result = self.call('follower', 'fetch_error')
                if result != "NONE":
                    self.bail("{} state after smart jerk".format(result))
                self.state = self.State.FOLLOW
            elif self.state == self.State.FOLLOW:
                self.call('follower', 'follow')
                self.call('follower', 'assign_states')
                result = self.call('follower', 'fetch_error')
                # Not handling lost line
                if result == "ON_INTERSECTION":
                    self.logger.info("Found intersection")
                    self.state = self.State.CENTER_ON_X
                elif result == "LARGE_OBJECT":
                    self.logger.info("Found large object")
                    self.state = self.State.CENTER_ON_BLUE
                else:
                    self.bail("{} state after follow".format(result))
            elif self.state == self.State.CENTER_ON_X:
                self.call('follower', 'center_on_intersection')
                self.call('follower', 'assign_states')
                result = self.call('follower', 'fetch_error')
                if result != "ON_INTERSECTION":
                    self.bail("{} state after center on X".format(result))
                self.state = self.State.ROTATE_ON_X
                sys.exit(0)
            elif self.state == self.State.ROTATE_ON_X:
                self.call('follower', 'rotate_on_x')
                self.call('follower', 'assign_states')
                result = self.call('follower', 'fetch_error')
                if result != "ON_INTERSECTION":
                    self.bail("{} state after rotate on X".format(result))
                self.state = self.State.FOLLOW_ON_X
            elif self.state == self.State.FOLLOW_ON_X:
                self.call('follower', 'follow', {"on_x": True})
                self.call('follower', 'assign_states')
                result = self.call('follower', 'fetch_error')
                if not (result == "LARGE_OBJECT" or result == "NONE"):
                    self.bail("{} state after rotate on X".format(result))
                self.state = self.State.CENTER_ON_BLUE
                # TODO: Nothing below this refactored to use returns!
            elif self.state == self.State.CENTER_ON_BLUE:
                self.call('follower', 'center_on_blue')
                self.blue_blocks += 1
                self.state = self.State.AIM
            elif self.state == self.State.AIM:
                self.logger.info("Aiming turret")
                self.call('gunner', 'aim')
                self.state = self.State.FIRE
            elif self.state == self.State.FIRE:
                self.logger.info("Firing gun")
                self.call('gunner', 'fire')
                self.darts_fired += 1
                self.state = self.State.CHOOSE_DIR_BLUE
            elif self.state == self.State.CHOOSE_DIR_BLUE:
                self.logger.info("Turning around from blue block")
                self.state = self.State.FOLLOW
            elif self.state == self.State.CENTER_ON_RED:
                self.call('follower', 'center_on_red')
                self.state = self.State.FINISH

        self.logger.info(str(self))  # terminal state report
        self.logger.info("Done!")

    def call(self, obj_name, method_name, param_dict=dict()):
        """Light wrapper around ctrl_client to handle result unpacking."""
        result = self.ctrl_client.call(obj_name, method_name, param_dict)
        if result['type'] == 'error':
            self.logger.error("API call error: {}".format(result['msg']))
            return None
        else:
            return result['call_return']

    def bail(self, msg):
        """Log error message and exit cleanly, stopping all systems.

        :param msg: Error message to log.
        :type msg: string

        """
        self.logger.error("Can't handle follower result: {}".format(result))
        self.call('ctrl', 'stop_full')
        sys.exit(1)


if __name__ == "__main__":
    Pilot().run()
