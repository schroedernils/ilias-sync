// Disposable integration-test host only. Drive the same AppKit controls as the
// app, without system-wide input injection or an Accessibility grant.
#import "updates.mm"

static void record(NSString *message) {
    NSString *path = NSProcessInfo.processInfo.environment[@"ILIAS_UPDATE_PROBE_LOG"];
    NSFileHandle *file = [NSFileHandle fileHandleForWritingAtPath:path];
    [file seekToEndOfFile];
    [file writeData:[[message stringByAppendingString:@"\n"] dataUsingEncoding:NSUTF8StringEncoding]];
    [file closeFile];
}

static NSButton *findButton(NSView *view, SEL action) {
    if ([view isKindOfClass:NSButton.class]) {
        NSButton *button = (NSButton *)view;
        if (button.action == action && button.enabled && !button.hiddenOrHasHiddenAncestor) return button;
    }
    for (NSView *child in view.subviews) {
        NSButton *button = findButton(child, action);
        if (button) return button;
    }
    return nil;
}

static void click(NSString *action, NSString *name, unsigned attempts = 80) {
    for (NSWindow *window in NSApp.windows) {
        if (!window.visible) continue;
        NSButton *button = findButton(window.contentView, NSSelectorFromString(action));
        if (button) {
            record(name);
            [button performClick:nil];
            return;
        }
    }
    if (!attempts) {
        record([@"ERROR native control not available: " stringByAppendingString:action]);
        exit(3);
    }
    dispatch_after(dispatch_time(DISPATCH_TIME_NOW, 100 * NSEC_PER_MSEC), dispatch_get_main_queue(), ^{
        click(action, name, attempts - 1);
    });
}

static BOOL qtModal = YES;
static int allowPresentation() { return !qtModal; }

@interface ProbeDriver : IliasUpdateUserDriver
@property BOOL accepted;
@end

@implementation ProbeDriver
- (void)showUpdateFoundWithAppcastItem:(SUAppcastItem *)item state:(SPUUserUpdateState *)state
    reply:(void (^)(SPUUserUpdateChoice))reply
{
    record(@"found signed update");
    [super showUpdateFoundWithAppcastItem:item state:state reply:reply];
    if (!self.pendingPresentation) {
        record(@"ERROR native prompt presented before the modal closed");
        exit(4);
    }
    dispatch_after(dispatch_time(DISPATCH_TIME_NOW, 200 * NSEC_PER_MSEC), dispatch_get_main_queue(), ^{
        if (!self.pendingPresentation) exit(4);
        qtModal = NO;
        ilias_updates_set_busy(0);
    });
}
- (void)presentUpdate:(SUAppcastItem *)item state:(SPUUserUpdateState *)state
    reply:(void (^)(SPUUserUpdateChoice))reply
{
    [super presentUpdate:item state:state reply:reply];
    dispatch_async(dispatch_get_main_queue(), ^{ click(@"installUpdate:", @"clicked native Install Update"); });
}
- (void)showDownloadDidStartExtractingUpdate {
    record(@"verified; extracting DMG");
    [super showDownloadDidStartExtractingUpdate];
}
- (void)showReadyToInstallAndRelaunch:(void (^)(SPUUserUpdateChoice))reply {
    [super showReadyToInstallAndRelaunch:^(SPUUserUpdateChoice choice) {
        self.accepted = choice == SPUUserUpdateChoiceInstall;
        reply(choice);
    }];
    dispatch_async(dispatch_get_main_queue(), ^{ click(@"installAndRestart:", @"clicked native Install and Relaunch"); });
}
- (void)showUpdateNotFoundWithError:(NSError *)error acknowledgement:(void (^)(void))ack {
    record([@"ERROR no update " stringByAppendingString:error.description]);
    ack();
    exit(5);
}
- (void)showUpdaterError:(NSError *)error acknowledgement:(void (^)(void))ack {
    record([@"ERROR " stringByAppendingString:error.description]);
    ack();
    exit(5);
}
- (void)dismissUpdateInstallation {
    [super dismissUpdateInstallation];
    if (self.accepted) dispatch_async(dispatch_get_main_queue(), ^{ [NSApp terminate:nil]; });
}
@end

@interface UpdateProbe : IliasUpdateDelegate <NSApplicationDelegate>
@end

@implementation UpdateProbe
- (void)applicationDidFinishLaunching:(NSNotification *)note {
    closed.store(false);
    ilias_updates_set_presentation_guard(allowPresentation);
    userDriver = [[ProbeDriver alloc] initWithHostBundle:NSBundle.mainBundle delegate:nil];
    updater = [[SPUUpdater alloc] initWithHostBundle:NSBundle.mainBundle applicationBundle:NSBundle.mainBundle
        userDriver:userDriver delegate:self];
    NSError *error = nil;
    if (![updater startUpdater:&error]) { record([@"ERROR " stringByAppendingString:error.description]); exit(2); }
    [updater checkForUpdates];
}
// Finish the install-on-quit path without starting a live IliasSync session.
- (BOOL)updaterShouldRelaunchApplication:(SPUUpdater *)sender { return NO; }
@end

int main() {
    @autoreleasepool {
        NSApplication *app = NSApplication.sharedApplication;
        [app setActivationPolicy:NSApplicationActivationPolicyAccessory];
        UpdateProbe *delegate = [UpdateProbe new];
        app.delegate = delegate;
        dispatch_after(dispatch_time(DISPATCH_TIME_NOW, 120 * NSEC_PER_SEC), dispatch_get_main_queue(), ^{
            record(@"ERROR integration probe timed out");
            exit(6);
        });
        [app run];
    }
    return 0;
}
