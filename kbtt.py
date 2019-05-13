import sys
import copy
import json


# common section
# --------------
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


def is_device_event(event):
    return event['t'] in (EventType.CONNECT, EventType.DISCONNECT,)

def is_connect_event(event):
    return event['t'] == EventType.CONNECT

def is_disconnect_event(event):
    return event['t'] == EventType.DISCONNECT

def is_pause_event(event):
    return event['t'] == EventType.PAUSE

def is_unpause_event(event):
    return event['t'] == EventType.UNPAUSE

def is_start_event(event):
    return event['t'] == EventType.START

def is_end_event(event):
    return event['t'] == EventType.END


# flatten section
# ---------------
def flattenEventStream(events, ttl, currentTime=None):
    events = copy.copy(events)
    events.sort(key=lambda x: x['c'])

    data = findDeviceStreams(events)
    deviceStreams, otherEvents = data['deviceStreams'], data['otherEvents']
    result = otherEvents
    for deviceId, devices in deviceStreams.items():
        result += flattenDeviceStream(devices, ttl, currentTime)
    result.sort(key=lambda x: x['c'])
    return result


def findDeviceStreams(events):
    deviceStreams = {}
    otherEvents = []
    paused = False
    for event in events:
        if is_device_event(event):
            if event['d'] not in deviceStreams:
                deviceStreams[event['d']] = []
            deviceStreams[event['d']].append(event)
        else:
            ignore = False
            if is_pause_event(event):
                ignore = paused
                paused = True
            elif is_unpause_event(event):
                ignore = not paused
                paused = False
            if not ignore:
                otherEvents.append(event)
            if is_end_event(event):
                break
    return {'deviceStreams': deviceStreams, 'otherEvents': otherEvents,}


def flattenDeviceStream(events, ttl, currentTime=None):
    if not events:
        return []

    lastEvent = events[0]
    result = [lastEvent]

    lastConnected = None
    if is_connect_event(lastEvent):
        lastConnected = lastEvent['c']

    for event in events:
        if is_connect_event(event):
            ignore = False
            if is_connect_event(lastEvent):
                if lastConnected is not None:
                    if event['c'] - lastConnected < ttl:
                        ignore = True
                    else:
                        result.append({
                            't': 'd',
                            'c': lastConnected + ttl / 2,
                            'u': event['u'],
                            'd': event['d']
                        })
            if not ignore:
                result.append(event)

            lastConnected = event['c']

        elif is_disconnect_event(event):

            if (is_connect_event(lastEvent) and lastConnected is not None and
                    event['c'] - lastConnected >= ttl):
                result.append({
                    't': 'd',
                    'c': lastConnected + ttl / 2,
                    'u': event['u'],
                    'd': event['d'],
                })
            elif not is_disconnect_event(lastEvent):
                result.append(event)

        lastEvent = result[-1]

    if (is_connect_event(lastEvent) and lastConnected is not None and
            currentTime is not None):
        if currentTime - lastConnected >= ttl:
            result.append({
                't': 'd',
                'c': lastConnected + ttl / 2,
                'u': lastEvent['u'],
                'd': lastEvent['d'],
            })

    return result


# reduce section
# --------------
def connected(connectedDevices):
    firstUserId = None
    for deviceId, userId in connectedDevices.items():
        if firstUserId is None:
            firstUserId = userId
        elif not firstUserId == userId:
            return True
    return False


def reduceEvents(events):
    trackedTime = 0
    connectedDevices= {}
    lastBothConnected = None
    lastActive = None
    paused = False
    stateTime = None
    for event in events:
        if is_connect_event(event):
            prevConnected = connected(connectedDevices)
            connectedDevices[event['d']] = event['u']
            if not prevConnected and connected(connectedDevices) and not paused:
                lastBothConnected = event['c']
                lastActive = event['c']
        elif is_disconnect_event(event):
            prevConnected = connected(connectedDevices)
            connectedDevices.pop(event['d'])
            if (prevConnected and lastBothConnected is not None and
                    not connected(connectedDevices) and not paused):
                trackedTime += event['c'] - lastBothConnected
                lastBothConnected = None
        elif is_pause_event(event):
            if lastBothConnected is not None and not paused:
                trackedTime += event['c'] - lastBothConnected
                lastBothConnected = None
            paused = True
        elif is_unpause_event(event):
            if connected(connectedDevices):
                lastBothConnected = event['c']
                lastActive = event['c']
            paused = False
        elif is_end_event(event):
            if lastBothConnected is not None and not paused:
                trackedTime += event['c'] - lastBothConnected
                lastBothConnected = None
            break

        stateTime = event['c']

    state = AppState.IDLE
    if paused:
        state = AppState.PAUSED
    elif connected(connectedDevices):
        state = AppState.IN_PROGRESS

    return {
        'trackedTime': trackedTime,
        'lastActive': lastActive,
        'stateTime': stateTime,
        'state': state,
    }


if __name__ == "__main__":
    data = json.loads(sys.stdin.read())
    events = flattenEventStream(data['events'],
                                data['ttl'], data['currentTime'])
    result = reduceEvents(events)
    data = json.dumps(result)

    sys.stdout.write(data)
