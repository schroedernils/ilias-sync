// SPDX-License-Identifier: GPL-3.0-or-later
// Build with C++17, ARC, AppKit and Sparkle 2.10.1. The host supplies the
// framework at @rpath/Sparkle.framework/Versions/B/Sparkle and the appcast/key
// in Info.plist. Omit SUEnableAutomaticChecks; set SUAutomaticallyUpdate and
// SUEnableSystemProfiling to NO. Never write preferences during initialization.
#import <AppKit/AppKit.h>
#import <Sparkle/Sparkle.h>
#include <atomic>

static std::atomic_bool busy{false};
static std::atomic_bool closed{true};
static SPUUpdater *updater;
static SPUStandardUserDriver *userDriver;
static BOOL started = NO;
static NSString *lastError;

@interface IliasUpdateDelegate : NSObject <SPUUpdaterDelegate>
@property (copy) void (^pendingInstallation)(void);
- (void)resumeWhenIdle;
@end

@implementation IliasUpdateDelegate
- (BOOL)updater:(SPUUpdater *)sender shouldPostponeRelaunchForUpdate:(SUAppcastItem *)item
    untilInvokingBlock:(void (^)(void))installHandler
{
    if (closed.load()) return YES;
    if (!busy.load()) return NO;
    self.pendingInstallation = installHandler;
    return YES;
}

- (BOOL)updater:(SPUUpdater *)sender willInstallUpdateOnQuit:(SUAppcastItem *)item
    immediateInstallationBlock:(void (^)(void))installHandler
{
    // Sparkle still installs on actual process termination, even on YES.
    // The host must veto quitting while its sync FileLock is held.
    if (closed.load()) return YES;
    if (!busy.load()) return NO;
    self.pendingInstallation = installHandler;
    return YES;
}

- (void)resumeWhenIdle
{
    // Avoid reentering the host from set_busy(). Recheck because another sync
    // or close() may arrive before the main queue processes this block.
    dispatch_async(dispatch_get_main_queue(), ^{
        if (closed.load() || busy.load()) return;
        void (^handler)(void) = self.pendingInstallation;
        self.pendingInstallation = nil;
        if (handler) handler();
    });
}
@end

static IliasUpdateDelegate *updateDelegate;

extern "C" const char *ilias_updates_last_error(void)
{
    if (![NSThread isMainThread]) return "Updater calls require the main thread.";
    return lastError.UTF8String;
}

extern "C" int ilias_updates_init(void)
{
    @autoreleasepool {
        if (![NSThread isMainThread]) return 0;
        if (updater) {
            lastError = @"An updater already owns Sparkle.";
            return 0;
        }
        @try {
            NSBundle *host = NSBundle.mainBundle;
            if (!host.bundleIdentifier) {
                lastError = @"Sparkle requires an application bundle identifier.";
                return 0;
            }
            lastError = nil;
            busy.store(false);
            closed.store(false);
            updateDelegate = [IliasUpdateDelegate new];
            userDriver = [[SPUStandardUserDriver alloc] initWithHostBundle:host delegate:nil];
            updater = [[SPUUpdater alloc] initWithHostBundle:host applicationBundle:host
                userDriver:userDriver delegate:updateDelegate];
            if (updater) return 1;
            lastError = @"Sparkle could not be initialized.";
        } @catch (NSException *exception) {
            lastError = exception.reason;
        }
        closed.store(true);
        updater = nil;
        userDriver = nil;
        updateDelegate = nil;
        return 0;
    }
}

extern "C" int ilias_updates_start(void)
{
    @autoreleasepool {
        if (![NSThread isMainThread] || closed.load() || !updater) return 0;
        if (started) return 1;
        @try {
            NSError *error = nil;
            started = [updater startUpdater:&error];
            lastError = started ? nil : (error.localizedDescription ?: @"Sparkle could not be started.");
            return started;
        } @catch (NSException *exception) {
            lastError = exception.reason;
            return 0;
        }
    }
}

extern "C" int ilias_updates_can_check(void)
{
    if (![NSThread isMainThread] || closed.load() || !started) return 0;
    return updater.canCheckForUpdates;
}

extern "C" int ilias_updates_check(void)
{
    @autoreleasepool {
        if (!ilias_updates_can_check()) return 0;
        @try {
            [updater checkForUpdates];
            return 1;
        } @catch (NSException *exception) {
            lastError = exception.reason;
            return 0;
        }
    }
}

extern "C" int ilias_updates_get_auto_check(void)
{
    if (![NSThread isMainThread] || closed.load()) return 0;
    return updater.automaticallyChecksForUpdates;
}

extern "C" void ilias_updates_set_auto_check(int enabled)
{
    if (![NSThread isMainThread] || closed.load()) return;
    updater.automaticallyChecksForUpdates = (enabled != 0);
}

extern "C" int ilias_updates_get_auto_download(void)
{
    if (![NSThread isMainThread] || closed.load()) return 0;
    return updater.automaticallyDownloadsUpdates;
}

extern "C" void ilias_updates_set_auto_download(int enabled)
{
    if (![NSThread isMainThread] || closed.load()) return;
    updater.automaticallyDownloadsUpdates = (enabled != 0);
}

extern "C" void ilias_updates_set_busy(int value)
{
    if (![NSThread isMainThread] || closed.load()) return;
    busy.store(value != 0);
    if (!value && updateDelegate.pendingInstallation) [updateDelegate resumeWhenIdle];
}

extern "C" void ilias_updates_close(void)
{
    @autoreleasepool {
        if (![NSThread isMainThread]) return;
        closed.store(true);
        busy.store(true);
        updateDelegate.pendingInstallation = nil;
        // SPUUpdater deallocation invalidates its timers and aborts its driver.
        // Keep the delegate alive through that abort; no preference is changed.
        updater = nil;
        userDriver = nil;
        updateDelegate = nil;
        started = NO;
    }
}
