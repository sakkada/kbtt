import unittest
from kbtt import AppState, TimeTracker


class TrackTest(unittest.TestCase):
    def setUp(self):
        self.tt = TimeTracker()

    def test_track(self):
        self.assertTrue('error' in self.tt.track(1))
        self.assertTrue('error' in self.tt.track(None))
        self.assertTrue('error' in self.tt.track(True))
        self.assertTrue('error' in self.tt.track('Invalid json'))
        self.assertTrue('error' in self.tt.track({'invalid': 'dict'}))

        self.assertFalse('error' in self.tt.track(
            {'events': [{'t': 's', 'c': 0},], 'ttl': 4, 'currentTime': 10}
        ))
        self.assertFalse('error' in self.tt.track(
            '{"events": [{"t": "s", "c": 0}], "ttl": 4, "currentTime": 10}'
        ))


class ReduceEventsTest(unittest.TestCase):
    def setUp(self):
        self.tt = TimeTracker()

    def test_reduce_tracked_time(self):
        # should be 0 with no users
        self.assertEqual(self.tt.reduce_events([
            {'t': 's', 'c': 0,},
        ])['trackedTime'], 0)

        # should be 0 with one user
        self.assertEqual(self.tt.reduce_events([
            {'t': 's', 'c': 0,},
            {'t': 'c', 'c': 1, 'u': 1, 'd': '1',},
            {'t': 'c', 'c': 2, 'u': 1, 'd': '2',},
        ])['trackedTime'], 0)

        # should track interval with both users connected
        self.assertEqual(self.tt.reduce_events([
            {'t': 'c', 'c': 0, 'u': 1, 'd': '1',},
            {'t': 'c', 'c': 1, 'u': 2, 'd': '2',},
            {'t': 'd', 'c': 3, 'u': 2, 'd': '2',},
        ])['trackedTime'], 2)

        # should track interval with end event
        self.assertEqual(self.tt.reduce_events([
            {'t': 'c', 'c': 0, 'u': 1, 'd': '1',},
            {'t': 'c', 'c': 1, 'u': 2, 'd': '2',},
            {'t': 'e', 'c': 3,},
        ])['trackedTime'], 2)

        # should handle pause with both users connected
        self.assertEqual(self.tt.reduce_events([
            {'t': 'c', 'c': 0, 'u': 1, 'd': '1',},
            {'t': 'c', 'c': 1, 'u': 2, 'd': '2',},
            {'t': 'p', 'c': 3,},
            {'t': 'u', 'c': 4,},
            {'t': 'e', 'c': 6,},
        ])['trackedTime'], 4)

        # should track connecting while pausing
        self.assertEqual(self.tt.reduce_events([
            {'t': 'c', 'c': 0, 'u': 1, 'd': '1',},
            {'t': 'p', 'c': 1,},
            {'t': 'c', 'c': 3, 'u': 2, 'd': '2',},
            {'t': 'u', 'c': 4,},
            {'t': 'e', 'c': 6,},
        ])['trackedTime'], 2)

        # shouldnt track unpausing while disconnected user
        self.assertEqual(self.tt.reduce_events([
            {'t': 'c', 'c': 0, 'u': 1, 'd': '1',},
            {'t': 'p', 'c': 1,},
            {'t': 'c', 'c': 3, 'u': 2, 'd': '2',},
            {'t': 'd', 'c': 4, 'u': 2, 'd': '2',},
            {'t': 'u', 'c': 5,},
            {'t': 'e', 'c': 6,},
        ])['trackedTime'], 0)

        # should end with end event
        self.assertEqual(self.tt.reduce_events([
            {'t': 'c', 'c': 0, 'u': 1, 'd': '1',},
            {'t': 'c', 'c': 0, 'u': 2, 'd': '2',},
            {'t': 'e', 'c': 3,},
            {'t': 'c', 'c': 4, 'u': 1, 'd': '1',},
            {'t': 'c', 'c': 4, 'u': 2, 'd': '2',},
            {'t': 'd', 'c': 5, 'u': 1, 'd': '1',},
            {'t': 'd', 'c': 5, 'u': 2, 'd': '2',},
        ])['trackedTime'], 3)

        # additional devices shouldnt change tracked time
        self.assertEqual(self.tt.reduce_events([
            {'t': 's', 'c': 0,},
            {'t': 'c', 'c': 0, 'u': 1, 'd': '1',},
            {'t': 'c', 'c': 0, 'u': 2, 'd': '2',},
            {'t': 'c', 'c': 10, 'u': 1, 'd': '3',},
            {'t': 'd', 'c': 50, 'u': 1, 'd': '3',},
            {'t': 'd', 'c': 100, 'u': 1, 'd': '1',},
            {'t': 'd', 'c': 100, 'u': 2, 'd': '2',},
        ])['trackedTime'], 100)

    def test_last_active(self):
        # should be null with one user
        self.assertEqual(self.tt.reduce_events([
            {'t': 'c', 'c': 0, 'u': 1, 'd': '1',},
            {'t': 'c', 'c': 1, 'u': 1, 'd': '2',},
        ])['lastActive'], None)

        # should be last connected time with two users
        self.assertEqual(self.tt.reduce_events([
            {'t': 'c', 'c': 0, 'u': 1, 'd': '1',},
            {'t': 'c', 'c': 1, 'u': 2, 'd': '2',},
        ])['lastActive'], 1)

        # should be unpaused time with two users
        self.assertEqual(self.tt.reduce_events([
            {'t': 'c', 'c': 0, 'u': 1, 'd': '1',},
            {'t': 'c', 'c': 1, 'u': 2, 'd': '2',},
            {'t': 'p', 'c': 2,},
            {'t': 'u', 'c': 3,},
        ])['lastActive'], 3)

        # should keep connected time with one user unpaused
        self.assertEqual(self.tt.reduce_events([
            {'t': 'c', 'c': 0, 'u': 1, 'd': '1',},
            {'t': 'c', 'c': 1, 'u': 2, 'd': '2',},
            {'t': 'p', 'c': 2,},
            {'t': 'd', 'c': 3, 'u': 1, 'd': '1',},
            {'t': 'u', 'c': 4,},
        ])['lastActive'], 1)

    def test_state_time(self):
        # should be null with empty events
        self.assertEqual(self.tt.reduce_events([])['stateTime'], None)

        # should be last event timestamp
        self.assertEqual(self.tt.reduce_events([
            {'t': 's', 'c': 0,},
            {'t': 'p', 'c': 1,},
        ])['stateTime'], 1)

    def test_state(self):
        # should be idle at start
        self.assertEqual(self.tt.reduce_events([
            {'t': 's', 'c': 0,},
        ])['state'], AppState.IDLE)

        # should be paused
        self.assertEqual(self.tt.reduce_events([
            {'t': 's', 'c': 0,},
            {'t': 'p', 'c': 1,},
        ])['state'], AppState.PAUSED)

        # should be unpaused
        self.assertEqual(self.tt.reduce_events([
            {'t': 's', 'c': 0,},
            {'t': 'p', 'c': 1,},
            {'t': 'u', 'c': 2,},
        ])['state'], AppState.IDLE)

        # should be idle with one user
        self.assertEqual(self.tt.reduce_events([
            {'t': 's', 'c': 0,},
            {'t': 'c', 'c': 1, 'u': 1, 'd': '1',},
        ])['state'], AppState.IDLE)

        # should be idle with one user from two devices
        self.assertEqual(self.tt.reduce_events([
            {'t': 's', 'c': 0,},
            {'t': 'c', 'c': 1, 'u': 1, 'd': '1',},
            {'t': 'c', 'c': 2, 'u': 1, 'd': '2',},
        ])['state'], AppState.IDLE)

        # should be in progress with two users
        self.assertEqual(self.tt.reduce_events([
            {'t': 's', 'c': 0,},
            {'t': 'c', 'c': 1, 'u': 1, 'd': '1',},
            {'t': 'c', 'c': 2, 'u': 2, 'd': '2',},
        ])['state'], AppState.IN_PROGRESS)

        # should be in progress with two users from two devices
        self.assertEqual(self.tt.reduce_events([
            {'t': 's', 'c': 0,},
            {'t': 'c', 'c': 1, 'u': 1, 'd': '1',},
            {'t': 'c', 'c': 2, 'u': 2, 'd': '2',},
            {'t': 'c', 'c': 3, 'u': 1, 'd': '3',},
            {'t': 'c', 'c': 4, 'u': 2, 'd': '4',},
        ])['state'], AppState.IN_PROGRESS)

        # should be paused with two users
        self.assertEqual(self.tt.reduce_events([
            {'t': 's', 'c': 0,},
            {'t': 'c', 'c': 1, 'u': 1, 'd': '1',},
            {'t': 'p', 'c': 2,},
            {'t': 'c', 'c': 3, 'u': 2, 'd': '2',},
        ])['state'], AppState.PAUSED)

        # should be idle when user disconnects
        self.assertEqual(self.tt.reduce_events([
            {'t': 'c', 'c': 0, 'u': 1, 'd': '1',},
            {'t': 'c', 'c': 1, 'u': 2, 'd': '2',},
            {'t': 'd', 'c': 2, 'u': 2, 'd': '2',},
        ])['state'], AppState.IDLE)


class FlattenTest(unittest.TestCase):
    def setUp(self):
        self.tt = TimeTracker()

    def test_flattenDeviceStream(self):
        # should be empty on empty input
        self.assertEqual(self.tt.flatten_device_stream([], 4, 4), [])

        # should flatten connect events
        self.assertEqual(self.tt.flatten_device_stream([
            {'t': 'c', 'c': 0, 'u': 1, 'd': '1',},
            {'t': 'c', 'c': 1, 'u': 1, 'd': '1',},
            {'t': 'c', 'c': 2, 'u': 1, 'd': '1',},
            {'t': 'c', 'c': 3, 'u': 1, 'd': '1',},
        ], 4, 4), [
            {'t': 'c', 'c': 0, 'u': 1, 'd': '1',},
        ])

        # should flatten connect events with disconnect siblings
        self.assertEqual(self.tt.flatten_device_stream([
            {'t': 'c', 'c': 0, 'u': 1, 'd': '1',},
            {'t': 'c', 'c': 1, 'u': 1, 'd': '1',},
            {'t': 'c', 'c': 2, 'u': 1, 'd': '1',},
            {'t': 'd', 'c': 3, 'u': 1, 'd': '1',},
        ], 4, 4), [
            {'t': 'c', 'c': 0, 'u': 1, 'd': '1',},
            {'t': 'd', 'c': 3, 'u': 1, 'd': '1',},
        ])

        # should add trailing disconnect event
        self.assertEqual(self.tt.flatten_device_stream([
            {'t': 'c', 'c': 0, 'u': 1, 'd': '1',},
            {'t': 'c', 'c': 1, 'u': 1, 'd': '1',},
            {'t': 'c', 'c': 2, 'u': 1, 'd': '1',},
            {'t': 'c', 'c': 3, 'u': 1, 'd': '1',},
        ], 4, 10), [
            {'t': 'c', 'c': 0, 'u': 1, 'd': '1',},
            {'t': 'd', 'c': 5, 'u': 1, 'd': '1',},
        ])

        # shouldnt add trailing disconnect event in advance
        self.assertEqual(self.tt.flatten_device_stream([
            {'t': 'c', 'c': 3, 'u': 1, 'd': '1',},
        ], 4, 5), [
            {'t': 'c', 'c': 3, 'u': 1, 'd': '1',},
        ])

        # should add disconnect events on timeout
        self.assertEqual(self.tt.flatten_device_stream([
            {'t': 'c', 'c': 0, 'u': 1, 'd': '1',},
            {'t': 'c', 'c': 5, 'u': 1, 'd': '1',},
        ], 4, 6), [
            {'t': 'c', 'c': 0, 'u': 1, 'd': '1',},
            {'t': 'd', 'c': 2, 'u': 1, 'd': '1',},
            {'t': 'c', 'c': 5, 'u': 1, 'd': '1',},
        ])

        # should flatten disconnect events
        self.assertEqual(self.tt.flatten_device_stream([
            {'t': 'd', 'c': 0, 'u': 1, 'd': '1',},
            {'t': 'd', 'c': 0, 'u': 1, 'd': '1',},
            {'t': 'd', 'c': 0, 'u': 1, 'd': '1',},
        ], 4, 10), [
            {'t': 'd', 'c': 0, 'u': 1, 'd': '1',},
        ])


        # should flatten injected disconnect events
        self.assertEqual(self.tt.flatten_device_stream([
            {'t': 'c', 'c': 0, 'u': 1, 'd': '1',},
            {'t': 'd', 'c': 6, 'u': 1, 'd': '1',},
        ], 4, 10), [
            {'t': 'c', 'c': 0, 'u': 1, 'd': '1',},
            {'t': 'd', 'c': 2, 'u': 1, 'd': '1',},
        ])

    def test_findDeviceStreams(self):
        # should find device streams, in js version deviceStreams keys are ints
        self.assertEqual(self.tt.find_device_streams([
            {'t': 's', 'c': 0,},
            {'t': 'c', 'c': 1, 'u': 1, 'd': '1',},
            {'t': 'p', 'c': 0,},
            {'t': 'c', 'c': 1, 'u': 2, 'd': '2',},
            {'t': 'd', 'c': 3, 'u': 1, 'd': '1',},
            {'t': 'u', 'c': 3,},
            {'t': 'e', 'c': 4,},
        ])[0], {
            '1': [
                {'t': 'c', 'c': 1, 'u': 1, 'd': '1',},
                {'t': 'd', 'c': 3, 'u': 1, 'd': '1',},
            ],
            '2': [
                {'t': 'c', 'c': 1, 'u': 2, 'd': '2',},
            ],
        })

        # should find other events
        self.assertEqual(self.tt.find_device_streams([
            {'t': 's', 'c': 0,},
            {'t': 'c', 'c': 1, 'u': 1, 'd': '1',},
            {'t': 'p', 'c': 0,},
            {'t': 'c', 'c': 1, 'u': 2, 'd': '2',},
            {'t': 'd', 'c': 3, 'u': 1, 'd': '1',},
            {'t': 'u', 'c': 3,},
            {'t': 'e', 'c': 4,},
        ])[1], [
            {'t': 's', 'c': 0,},
            {'t': 'p', 'c': 0,},
            {'t': 'u', 'c': 3,},
            {'t': 'e', 'c': 4,},
        ])

    def test_flatten_event_stream(self):
        # should sort input
        self.assertEqual(self.tt.flatten_event_stream([
            {'t': 's', 'c': 1,},
            {'t': 'c', 'c': 2, 'u': 1, 'd': '1',},
            {'t': 'd', 'c': 4, 'u': 1, 'd': '1',},
            {'t': 'e', 'c': 3,},
        ], 4, 4), [
            {'t': 's', 'c': 1,},
            {'t': 'c', 'c': 2, 'u': 1, 'd': '1',},
            {'t': 'e', 'c': 3,},
        ])

        # should flatten app stream
        self.assertEqual(self.tt.flatten_event_stream([
            {'t': 's', 'c': 0,},
            {'t': 'p', 'c': 1,},
            {'t': 'c', 'c': 2, 'u': 1, 'd': '1',},
            {'t': 'c', 'c': 3, 'u': 2, 'd': '2',},
            {'t': 'c', 'c': 6, 'u': 1, 'd': '1',},
            {'t': 'u', 'c': 7,},
        ], 4, 10), [
            {'t': 's', 'c': 0,},
            {'t': 'p', 'c': 1,},
            {'t': 'c', 'c': 2, 'u': 1, 'd': '1',},
            {'t': 'c', 'c': 3, 'u': 2, 'd': '2',},
            {'t': 'd', 'c': 4, 'u': 1, 'd': '1',},
            {'t': 'd', 'c': 5, 'u': 2, 'd': '2',},
            {'t': 'c', 'c': 6, 'u': 1, 'd': '1',},
            {'t': 'u', 'c': 7,},
            {'t': 'd', 'c': 8, 'u': 1, 'd': '1',},
        ])

        # should skip duplicate pause events
        self.assertEqual(self.tt.flatten_event_stream([
            {'t': 'p', 'c': 1,},
            {'t': 'p', 'c': 2,},
            {'t': 'u', 'c': 3,},
            {'t': 'u', 'c': 4,},
        ], 4, 10), [
            {'t': 'p', 'c': 1,},
            {'t': 'u', 'c': 3,},
        ])

        # should stop on end event
        self.assertEqual(self.tt.flatten_event_stream([
            {'t': 's', 'c': 1,},
            {'t': 'p', 'c': 2,},
            {'t': 'e', 'c': 3,},
            {'t': 'u', 'c': 4,},
        ], 4, 10), [
            {'t': 's', 'c': 1,},
            {'t': 'p', 'c': 2,},
            {'t': 'e', 'c': 3,},
        ])


if __name__ == "__main__":
    unittest.main()
