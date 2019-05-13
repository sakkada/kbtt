import sys
import json


class EventType:
    START = 's'
    END = 'e'
    PAUSE = 'p'
    UNPAUSE = 'u'
    CONNECT = 'c'
    DISCONNECT = 'd'


class AppState:
    IDLE = 0
    IN_PROGRESS = 1
    PAUSED = 2


class TimeTracker:
    def track(self, value):
        if isinstance(value, str):
            try:
                value = json.loads(value)
            except json.JSONDecodeError:
                value = None

        if not (isinstance(value, dict) and
                all([i in value for i in ('events', 'ttl', 'currentTime',)])):
            return {'error': 'Invalid input value. JSON or dict are allowed.'}

        events = self.flatten_event_stream(value['events'], value['ttl'],
                                           value['currentTime'])
        return self.reduce_events(events)

    # event checkers
    def is_device_event(self, event):
        return event['t'] in (EventType.CONNECT, EventType.DISCONNECT,)

    def is_connect_event(self, event):
        return event['t'] == EventType.CONNECT

    def is_disconnect_event(self, event):
        return event['t'] == EventType.DISCONNECT

    def is_pause_event(self, event):
        return event['t'] == EventType.PAUSE

    def is_unpause_event(self, event):
        return event['t'] == EventType.UNPAUSE

    def is_start_event(self, event):
        return event['t'] == EventType.START

    def is_end_event(self, event):
        return event['t'] == EventType.END

    # flatten methods
    def flatten_event_stream(self, events, ttl, current_time=None):
        events = events[:]
        events.sort(key=lambda x: x['c'])

        device_streams, result = self.find_device_streams(events)
        for devices in device_streams.values():
            result += self.flatten_device_stream(devices, ttl, current_time)
        result.sort(key=lambda x: x['c'])
        return result

    def find_device_streams(self, events):
        device_streams, other_events = {}, []

        paused = False
        for event in events:
            if self.is_device_event(event):
                if event['d'] not in device_streams:
                    device_streams[event['d']] = []
                device_streams[event['d']].append(event)
            else:
                ignore = False
                if self.is_pause_event(event):
                    ignore = paused
                    paused = True
                elif self.is_unpause_event(event):
                    ignore = not paused
                    paused = False
                if not ignore:
                    other_events.append(event)
                if self.is_end_event(event):
                    break

        return device_streams, other_events

    def flatten_device_stream(self, events, ttl, current_time=None):
        if not events:
            return []

        last_event = events[0]
        result = [last_event]

        last_connected = None
        if self.is_connect_event(last_event):
            last_connected = last_event['c']

        for event in events:
            if self.is_connect_event(event):
                ignore = False
                if (self.is_connect_event(last_event) and
                        last_connected is not None):
                    if event['c'] - last_connected < ttl:
                        ignore = True
                    else:
                        result.append({
                            't': 'd',
                            'c': last_connected + ttl / 2,
                            'u': event['u'],
                            'd': event['d']
                        })
                if not ignore:
                    result.append(event)
                last_connected = event['c']

            elif self.is_disconnect_event(event):
                if (self.is_connect_event(last_event) and
                        last_connected is not None and
                        event['c'] - last_connected >= ttl):
                    result.append({
                        't': 'd',
                        'c': last_connected + ttl / 2,
                        'u': event['u'],
                        'd': event['d'],
                    })
                elif not self.is_disconnect_event(last_event):
                    result.append(event)

            last_event = result[-1]

        if (self.is_connect_event(last_event) and
                last_connected is not None and current_time is not None and
                current_time - last_connected >= ttl):
            result.append({
                't': 'd',
                'c': last_connected + ttl / 2,
                'u': last_event['u'],
                'd': last_event['d'],
            })

        return result

    # reduce methods
    def is_both_connected(self, connected_devices):
        return len(set(connected_devices.values())) > 1

    def reduce_events(self, events):
        tracked_time = 0
        connected_devices = {}
        last_both_connected = None
        last_active = None
        paused = False
        state_time = None
        for event in events:
            if self.is_connect_event(event):
                prev_connected = self.is_both_connected(connected_devices)
                connected_devices[event['d']] = event['u']
                if (not prev_connected and not paused and
                        self.is_both_connected(connected_devices)):
                    last_both_connected = event['c']
                    last_active = event['c']
            elif self.is_disconnect_event(event):
                prev_connected = self.is_both_connected(connected_devices)
                connected_devices.pop(event['d'])
                if (prev_connected and
                        last_both_connected is not None and not paused and
                        not self.is_both_connected(connected_devices)):
                    tracked_time += event['c'] - last_both_connected
                    last_both_connected = None
            elif self.is_pause_event(event):
                if last_both_connected is not None and not paused:
                    tracked_time += event['c'] - last_both_connected
                    last_both_connected = None
                paused = True
            elif self.is_unpause_event(event):
                if self.is_both_connected(connected_devices):
                    last_both_connected = event['c']
                    last_active = event['c']
                paused = False
            elif self.is_end_event(event):
                if last_both_connected is not None and not paused:
                    tracked_time += event['c'] - last_both_connected
                    last_both_connected = None
                break

            state_time = event['c']

        state = AppState.IDLE
        if paused:
            state = AppState.PAUSED
        elif self.is_both_connected(connected_devices):
            state = AppState.IN_PROGRESS

        return {
            'trackedTime': tracked_time,
            'lastActive': last_active,
            'stateTime': state_time,
            'state': state,
        }


if __name__ == '__main__':
    if sys.stdin.isatty():
        data = {'error': 'Input stream is unavailable.'}
    else:
        data = TimeTracker().track(sys.stdin.read())
    sys.stdout.write(json.dumps(data))
