from abc import ABC, abstractmethod
import math
import signal
import time

# TODO: Explain module structure:
# - IDs only affect DQ order


class Game:

    # ~~~ MAIN STATE AND SIMULATION CODE ~~~

    def __init__(self, strategies, iterations, infinite=False,
                 debug_level=0, time_allowance=10):
        # Create player from strategy
        self._players = tuple(s(self, i)
                              for i, s in enumerate(strategies))

        # Record game parameters
        self._iterations = iterations
        self._infinite = infinite

        # Initialise game state
        self._scores = (0, 0)
        self._turn = 0
        self._dq = (False, False)
        self._history = (
            {'action': [], 'intention': [], 'response': []},
            {'action': [], 'intention': [], 'response': []}
        )
        self._honesty = (
            {'intention': [], 'response': []},
            {'intention': [], 'response': []}
        )

        # Setup time elapsed alarm
        signal.signal(signal.SIGALRM, lambda s, f: Game.raiseTimeLimitError())

        self._simulate()

    def _simulate(self):
        while self._turn < self._iterations:
            self._turn += 1
            # Make requests to players
            self._t = tuple(self.time_allowance for __ in range(2))
            try:
                self._request('intention')
                self._request('response')
                self._request('action')
            except DisqualificationError:
                self._scores = tuple(100 * self.iterations * (not dq)
                                     for dq in self._dq)
                break

            # Update helper properties
            self._update_honesty()

            # Update scores
            if all(self._history[i]['action'][-1] == 0 for i in (0, 1)):
                self._scores[0] += 50
                self._scores[1] += 50
            elif self._history[0]['action'][-1] == 0:
                self._scores[1] += 100
            elif self._history[1]['action'][-1] == 0:
                self._scores[0] += 100

    def _request(self, type_):
        for i in (0, 1):
            signal.alarm(self._t[i])
            start = time.time()
            try:
                res = getattr(self._players[i], f'state_{type_}')
                if not getattr(self, f'_validate_{type_}'):
                    raise InvalidResponseError
                self._history[i][type_].append(res)
            except Exception:
                self._dq[i]
                raise DisqualificationError
            signal.alarm(0)
            self._t[i] -= math.floor(time.time() - start)

    def _update_honesty(self):
        # Honesty of players' intentions
        for i in (0, 1):
            if self._history[i]['intention'][-1] is None:
                self._honesty[i]['intention'].append(None)
            else:
                self.honesty[i]['intention'].append(
                    int(self.history[i]['action'][-1] ==
                        self.history[i]['intention'][-1])
                )

        # Only update response honesty after second move
        if not self._turn:
            return

        # Honesty of players' responses
        for i in (0, 1):
            j = i ^ 1
            if self._history[i]['response'][-2] is None:
                self._honesty[i]['response'].append(None)
            else:
                action = self._history[j]['action'][-2]
                self._honesty[i]['response'].append(
                    int(self._history[i]['action'][-1] ==
                        self._history[i]['response'][-2][action])
                )

    def _parse_attribute(self, attr, id_, type_):
        if id_ and type_:
            return getattr(self, attr)[id_][type_]
        elif id_:
            return getattr(self, attr)[id_]
        elif type_:
            return tuple(getattr(self, attr)[i][type_] for i in (0, 1))
        else:
            return getattr(self, attr)

    # ~~~ GETTER METHODS FOR PRIVATE ATTRIBUTES ~~~

    def get_iterations(self):
        return None if self.infinite else self._iterations

    def get_infinite(self):
        return self._infinite

    def get_scores(self, id_=None):
        return self._scores[id_] if id_ else self._scores

    def get_turn(self):
        return self._turn

    def get_history(self, id_=None, type_=None):
        return self._parse_attribute('_history', id_, type_)

    def get_honesty(self, id_=None, type_=None):
        return self._parse_attribute('_honesy', id_, type_)

    # ~~~ STATIC METHODS FOR VALIDATION AND ERROR HANDLING ~~~

    @staticmethod
    def validate_intention(int_):
        return int_ is None or int_ in (0, 1)

    @staticmethod
    def validate_response(res):
        if res is None:
            return True
        if isinstance(res, dict) and \
                set(res.keys()) == {0, 1} and \
                all(res[k] in (0, 1) for k in (0, 1)):
            return True
        return False

    @staticmethod
    def validate_action(act):
        return act in (0, 1)

    @staticmethod
    def raiseTimeLimitError():
        raise TimeLimitError


class BaseStrategy(ABC):

    def __init__(self, game, id_):
        # Assign to game and record ID
        self.game = game
        self.my_id = id_
        self.op_id = id_ ^ 0

    @abstractmethod
    def state_action(self):
        pass

    def state_intention(self):
        return None

    def state_response(self):
        return None


class DisqualificationError(Exception):
    pass


class TimeLimitError(Exception):
    pass


class InvalidResponseError(Exception):
    pass
