# Internet Connection Monitoring Integration

This document describes the internet connection monitoring functionality added to DuneBugger Remote.

## Overview

The internet connection monitoring system ensures that WebSocket connections are only attempted when internet connectivity is available, and automatically reconnects when internet service is restored.

## Recent Fixes and Improvements

### Version 2.0 Enhancements (Latest)

#### 1. **Async Event Loop Management**
- **Fixed**: Event loop context preservation across threads
- **Added**: `main_event_loop` reference storage for cross-thread async operations
- **Improved**: Proper handling of `asyncio.run_coroutine_threadsafe()` calls

#### 2. **Connection Retry Logic Overhaul**
- **Replaced**: Problematic dual-thread monitoring with smart retry scheduling
- **Added**: `_schedule_connection_retry()` with exponential backoff
- **Fixed**: Race conditions in retry attempts
- **Improved**: Thread-safe retry flag management

#### 3. **Internet Monitor Integration**
- **Added**: Proper callback-based internet state notifications
- **Fixed**: Dependency injection in `WebPubSubListener` constructor
- **Improved**: Clean separation of concerns between monitoring and reconnection

#### 4. **Enhanced Error Handling**
- **Added**: Distinction between internet loss and WebSocket disconnection
- **Improved**: Graceful cleanup of failed connections
- **Fixed**: Proper client cleanup during retry attempts
- **Added**: Connection state tracking (`should_be_connected`)

#### 5. **Configuration Improvements**
- **Added**: Configurable test domain, check interval, and timeout settings
- **Updated**: Settings validation for new internet monitoring parameters
- **Improved**: Runtime configuration via environment variables

## Components

### 1. Internet Monitor (`internet_monitor.py`)

The `InternetConnectionMonitor` class provides:

- **Continuous monitoring**: Checks internet connectivity at configurable intervals (default: 7 seconds)
- **Multiple detection methods**: Uses DNS resolution and HTTPS connectivity tests
- **Callback system**: Notifies registered listeners when connection state changes
- **Thread-safe operations**: Safe to use across multiple threads
- **Configurable testing**: Customizable test domain and timeout values

#### Key Features:

- **Robust detection**: DNS resolution followed by HTTP request validation
- **Efficient monitoring**: Minimal resource usage with configurable check intervals
- **Event-driven**: Callbacks allow immediate response to connectivity changes
- **Global instance**: Shared `internet_monitor` instance configured from settings
- **Graceful error handling**: Continues monitoring even if individual checks fail

### 2. Enhanced WebPubSubListener

The `WebPubSubListener` class has been completely rewritten with:

- **Event loop awareness**: Proper asyncio event loop management across threads
- **Smart retry logic**: Intelligent connection retry with backoff and conditions
- **Internet state integration**: Deep integration with internet monitor callbacks
- **Connection state tracking**: Knows when it should be connected vs. when it shouldn't
- **Cross-thread async execution**: Safe execution of async operations from callback threads

#### Major Improvements:

1. **Removed problematic monitoring threads**: Eliminated race conditions and resource leaks
2. **Added proper async/await patterns**: Better integration with asyncio event loops
3. **Enhanced connection lifecycle**: Clear separation between setup, connection, and cleanup
4. **Improved error recovery**: Distinguishes between different types of failures
5. **Thread-safe operations**: Proper synchronization for multi-threaded callbacks

#### Integration Points:

1. **Startup**: Checks internet before initial connection
2. **Connection events**: Responds to internet state changes
3. **Message sending**: Validates connectivity before sending messages
4. **Error handling**: Different behavior for internet vs. WebSocket failures

## Usage

### Basic Setup

The internet monitor is automatically initialized when WebSocket is enabled:

```python
# In class_factory.py
if settings.websocketEnabled is True:
    internet_monitor.start_monitoring()
```

### Manual Control

You can manually control the monitor:

```python
from internet_monitor import internet_monitor

# Check current status
is_connected = internet_monitor.get_connection_status()

# Start/stop monitoring
internet_monitor.start_monitoring()
internet_monitor.stop_monitoring()

# Add callbacks
def on_connected():
    print("Internet restored!")

internet_monitor.add_connected_callback(on_connected)
```

### Configuration

The internet monitor is automatically configured from settings:

```python
# In dunebugger.conf
[Websocket]
testDomain = smart.dunebugger.it
connectionIntervalSecs = 7
connectionTimeoutSecs = 2
```

Or create a custom monitor:

```python
# Custom monitor with different settings
monitor = InternetConnectionMonitor(
    test_domain="example.com",
    check_interval=15,  # Check every 15 seconds
    timeout=3          # 3 second timeout for tests
)
```

### Key Configuration Parameters

- **testDomain**: Domain used for connectivity testing (default: smart.dunebugger.it)
- **connectionIntervalSecs**: Seconds between connectivity checks (default: 7)
- **connectionTimeoutSecs**: Timeout for each connectivity test (default: 2)

## Architecture Improvements

### Event Loop Management

The latest version addresses critical asyncio event loop issues:

```python
# Proper event loop capture during setup
async def _setup_client(self):
    self.main_event_loop = asyncio.get_running_loop()
    # ... client setup
```

This enables safe cross-thread async operations:

```python
# Safe async execution from callback threads
if self.main_event_loop and self.main_event_loop.is_running():
    asyncio.run_coroutine_threadsafe(
        self.handle_message(e.data), 
        self.main_event_loop
    )
```

### Connection State Management

Smart connection state tracking prevents unnecessary operations:

```python
class WebPubSubListener:
    def __init__(self, ...):
        self.should_be_connected = False  # Intent to be connected
        self.connection_retry_scheduled = False  # Prevent retry loops
```

### Retry Logic Improvements

Intelligent retry scheduling with proper conditions:

```python
def _schedule_connection_retry(self, delay=10):
    # Prevent multiple concurrent retries
    if self.connection_retry_scheduled:
        return
    
    # Check conditions before scheduling
    if not self.should_be_connected or not internet_available:
        return
    
    # Safe threaded retry with event loop integration
    retry_thread = threading.Thread(target=retry_connection, daemon=True)
```

## Connection Flow

### Normal Operation

1. Application starts with `asyncio.run(main())`
2. Internet monitor initializes and begins checking connectivity  
3. WebSocket client stores reference to main event loop during setup
4. If internet is available, WebSocket connects and joins group
5. Monitor continues periodic checks (every 7 seconds by default)
6. WebSocket operates normally with proper async message handling

### Internet Loss Detection

1. Monitor detects connectivity loss via DNS/HTTP checks
2. Notifies WebPubSubListener via `_on_internet_disconnected()` callback
3. WebSocket disconnection is handled gracefully in `_handle_websocket_disconnection()`
4. Connection retry scheduling is prevented while offline
5. Message sending operations check connectivity and abort if needed

### Internet Restoration Process

1. Monitor detects connectivity restoration via periodic checks
2. Calls `_on_internet_connected()` callback from monitor thread
3. Callback schedules reconnection using `run_coroutine_threadsafe()`
4. `_handle_internet_reconnection()` runs in main event loop context
5. Waits for network stabilization (3 seconds)
6. Attempts connection via `_attempt_connection()`
7. On success: joins group and sends heartbeat
8. On failure: schedules retry with exponential backoff

### Retry Mechanism

1. Connection failures trigger `_schedule_connection_retry()`
2. Retry flag prevents multiple concurrent retry attempts
3. Threaded delay mechanism waits before retry
4. Conditions checked before actual retry (should_be_connected, internet_available)
5. Retry attempts use proper event loop context
6. Multiple retry attempts with increasing delays until success

## Error Handling

### Connection Failures

- **Internet unavailable**: Connection attempts are skipped with clear logging
- **WebSocket failure with internet**: Automatic retry with exponential backoff (15s, 30s, etc.)
- **Authentication failures**: Handled by existing auth logic with proper cleanup
- **Event loop errors**: Fallback to threaded retry mechanisms

### Monitor Failures

- **DNS resolution failures**: Falls back to HTTP request validation
- **HTTP request failures**: Logs failure but continues monitoring cycle
- **Callback errors**: Individual callback failures don't stop other callbacks or monitoring
- **Thread synchronization**: Proper locking prevents race conditions

### New Error Scenarios

- **Event loop not available**: Graceful fallback to threaded reconnection
- **Client cleanup failures**: Errors during cleanup are caught and logged
- **Retry scheduling conflicts**: Duplicate retry attempts are prevented
- **Cross-thread async failures**: Proper error handling with event loop validation

## Logging

The system provides comprehensive logging:

- **INFO**: Connection state changes, major events
- **DEBUG**: Periodic status, detailed connection attempts
- **WARNING**: Temporary issues, retry attempts
- **ERROR**: Serious failures requiring attention

## Testing

Use the provided test script to verify functionality:

```bash
cd /home/marco/localGits/dunebugger-app/dunebugger-remote
python test_internet_integration.py
```

This tests:
- Internet connectivity detection
- Monitor start/stop functionality
- Callback system
- Integration with WebSocket components

## Performance Considerations

- **Check interval**: 7-second default balances responsiveness with resource usage
- **Timeout values**: 2-second timeout prevents long blocks while allowing for network latency
- **Thread usage**: Single monitor thread + event-driven retry threads
- **Memory usage**: Minimal overhead with efficient state tracking and cleanup
- **Event loop efficiency**: Proper async/await patterns reduce blocking operations

## Recent Bug Fixes

### Critical Fixes in Latest Version

1. **Event Loop Threading Issues**
   - **Problem**: "no running event loop" errors when callbacks tried to execute async code
   - **Solution**: Capture and store main event loop reference during client setup
   - **Impact**: Eliminates async execution errors from callback threads

2. **Connection Retry Race Conditions**
   - **Problem**: Multiple concurrent retry attempts causing connection conflicts
   - **Solution**: Retry scheduling flag and thread-safe retry logic
   - **Impact**: Stable reconnection behavior without resource leaks

3. **Internet Monitor Integration**
   - **Problem**: WebSocket class was trying to implement its own internet checking
   - **Solution**: Proper dependency injection and callback-based integration
   - **Impact**: Clean separation of concerns and reliable connectivity detection

4. **Client Cleanup Issues**
   - **Problem**: Failed connections left dangling client objects
   - **Solution**: Comprehensive cleanup in try/except blocks
   - **Impact**: No resource leaks from failed connection attempts

5. **Configuration Management**
   - **Problem**: Hard-coded connectivity parameters
   - **Solution**: Configurable test domain, intervals, and timeouts
   - **Impact**: Easy customization for different network environments

## Troubleshooting

### Common Issues

1. **Event loop errors**: If you see "no running event loop" messages:
   - Check that WebSocket is started from within an async context
   - Verify main event loop is properly captured during setup
   - Enable DEBUG logging to trace event loop operations

2. **Slow reconnection**: If WebSocket takes too long to reconnect:
   - Check `connectionIntervalSecs` setting (default: 7 seconds)
   - Verify `testDomain` is reachable from your network
   - Check authentication token validity
   - Review WebSocket server status

3. **False connection states**: If internet is detected incorrectly:
   - Verify `testDomain` setting points to a reliable server
   - Check firewall settings for DNS and HTTPS traffic
   - Adjust `connectionTimeoutSecs` for slow networks
   - Test manually: `curl https://smart.dunebugger.it`

4. **Callback errors**: If connection state callbacks fail:
   - Check callback function implementations for exceptions
   - Review error logs for specific issues
   - Ensure callbacks don't block for long periods
   - Verify thread safety in callback code

5. **Retry loops**: If connection retries become excessive:
   - Check for authentication failures in logs
   - Verify WebSocket server is accessible
   - Review retry backoff timing in DEBUG logs
   - Ensure `should_be_connected` flag is managed correctly

### Debug Mode

Enable detailed logging for troubleshooting:

```python
import logging
logging.getLogger('dunebuggerLog').setLevel(logging.DEBUG)
```

This provides detailed information about:
- Internet connectivity check results (DNS + HTTP)
- Event loop context and thread information
- Connection attempts and detailed failure reasons
- Callback executions and timing
- Retry scheduling and conditions
- Error conditions and recovery attempts

### Configuration Tuning

For unreliable networks:
```ini
[Websocket]
connectionIntervalSecs = 10  # Slower checks
connectionTimeoutSecs = 5    # Longer timeouts
```

For fast networks:
```ini
[Websocket]
connectionIntervalSecs = 5   # Faster checks
connectionTimeoutSecs = 1    # Shorter timeouts
```