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
@class IliasUpdateUserDriver;
static IliasUpdateUserDriver *userDriver;
static BOOL started = NO;
static NSString *lastError;
static int (*presentationGuard)(void);

static BOOL canPresentUpdate(void)
{
    return !presentationGuard || presentationGuard();
}

@interface IliasUpdateUserDriver : SPUStandardUserDriver
@property (copy) void (^pendingPresentation)(void);
- (void)resumePresentation;
@end

@implementation IliasUpdateUserDriver
- (void)resumePresentation
{
    if (closed.load() || !self.pendingPresentation || !canPresentUpdate()) return;
    void (^show)(void) = self.pendingPresentation;
    self.pendingPresentation = nil;
    show();
}

- (void)showUpdatePermissionRequest:(SPUUpdatePermissionRequest *)request
    reply:(void (^)(SUUpdatePermissionResponse *))reply
{
    __weak IliasUpdateUserDriver *driver = self;
    self.pendingPresentation = ^{ [driver presentPermission:request reply:reply]; };
    [self resumePresentation];
}

- (void)presentPermission:(SPUUpdatePermissionRequest *)request reply:(void (^)(SUUpdatePermissionResponse *))reply
{
    [super showUpdatePermissionRequest:request reply:reply];
}

- (void)showUpdateFoundWithAppcastItem:(SUAppcastItem *)item state:(SPUUserUpdateState *)state
    reply:(void (^)(SPUUserUpdateChoice))reply
{
    __weak IliasUpdateUserDriver *driver = self;
    self.pendingPresentation = ^{ [driver presentUpdate:item state:state reply:reply]; };
    [self resumePresentation];
}

- (void)presentUpdate:(SUAppcastItem *)item state:(SPUUserUpdateState *)state
    reply:(void (^)(SPUUserUpdateChoice))reply
{
    [super showUpdateFoundWithAppcastItem:item state:state reply:reply];
}

- (void)showUpdateInFocus
{
    if (self.pendingPresentation) [self resumePresentation];
    else [super showUpdateInFocus];
}

- (void)dismissUpdateInstallation
{
    self.pendingPresentation = nil;
    [super dismissUpdateInstallation];
}
@end

@interface IliasUpdateDelegate : NSObject <SPUUpdaterDelegate>
@property (copy) void (^pendingInstallation)(void);
- (void)resumeWhenIdle;
@end

@implementation IliasUpdateDelegate
- (BOOL)updater:(SPUUpdater *)sender shouldPostponeRelaunchForUpdate:(SUAppcastItem *)item
    untilInvokingBlock:(void (^)(void))installHandler
{
    if (closed.load()) return YES;
    if (!busy.load() && canPresentUpdate()) return NO;
    self.pendingInstallation = installHandler;
    return YES;
}

- (BOOL)updater:(SPUUpdater *)sender willInstallUpdateOnQuit:(SUAppcastItem *)item
    immediateInstallationBlock:(void (^)(void))installHandler
{
    // Sparkle still installs on actual process termination, even on YES.
    // The host must veto quitting while its sync FileLock is held.
    if (closed.load()) return YES;
    if (!busy.load() && canPresentUpdate()) return NO;
    self.pendingInstallation = installHandler;
    return YES;
}

- (void)resumeWhenIdle
{
    // Avoid reentering the host from set_busy(). Recheck because another sync
    // or close() may arrive before the main queue processes this block.
    dispatch_async(dispatch_get_main_queue(), ^{
        if (closed.load() || busy.load() || !canPresentUpdate()) return;
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
            userDriver = [[IliasUpdateUserDriver alloc] initWithHostBundle:host delegate:nil];
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
    // Qt's timer keeps running while a Qt modal is open. Present on a later
    // main-queue turn so polling never reenters Qt with an AppKit alert.
    if (userDriver.pendingPresentation) {
        dispatch_async(dispatch_get_main_queue(), ^{ [userDriver resumePresentation]; });
    }
}

extern "C" void ilias_updates_set_presentation_guard(int (*guard)(void))
{
    if ([NSThread isMainThread] && !closed.load()) presentationGuard = guard;
}

extern "C" void ilias_updates_close(void)
{
    @autoreleasepool {
        if (![NSThread isMainThread]) return;
        closed.store(true);
        busy.store(true);
        presentationGuard = nullptr;
        userDriver.pendingPresentation = nil;
        updateDelegate.pendingInstallation = nil;
        // SPUUpdater deallocation invalidates its timers and aborts its driver.
        // Keep the delegate alive through that abort; no preference is changed.
        updater = nil;
        userDriver = nil;
        updateDelegate = nil;
        started = NO;
    }
}
