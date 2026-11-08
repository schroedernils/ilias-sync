// Disposable integration-test host only. Never included in production packages.
#import <AppKit/AppKit.h>
#import <Sparkle/Sparkle.h>

static void record(NSString *message) {
    NSString *path = NSProcessInfo.processInfo.environment[@"ILIAS_UPDATE_PROBE_LOG"];
    if (!path) return;
    NSFileHandle *file = [NSFileHandle fileHandleForWritingAtPath:path];
    [file seekToEndOfFile];
    [file writeData:[[message stringByAppendingString:@"\n"] dataUsingEncoding:NSUTF8StringEncoding]];
    [file closeFile];
}

@interface UpdateProbe : NSObject <SPUUserDriver, SPUUpdaterDelegate, NSApplicationDelegate>
@property SPUUpdater *updater;
@property BOOL accepted;
@end

@implementation UpdateProbe
- (void)applicationDidFinishLaunching:(NSNotification *)note {
    self.updater = [[SPUUpdater alloc] initWithHostBundle:NSBundle.mainBundle
        applicationBundle:NSBundle.mainBundle userDriver:self delegate:self];
    NSError *error = nil;
    if (![self.updater startUpdater:&error]) { record([@"ERROR " stringByAppendingString:error.description]); exit(2); }
    [self.updater checkForUpdates];
}
- (BOOL)updaterShouldRelaunchApplication:(SPUUpdater *)updater { return NO; }
- (void)showUpdatePermissionRequest:(SPUUpdatePermissionRequest *)request reply:(void (^)(SUUpdatePermissionResponse *))reply {
    record(@"ERROR unexpected automatic-check permission request"); exit(3);
}
- (void)showUserInitiatedUpdateCheckWithCancellation:(void (^)(void))cancellation { record(@"checking"); }
- (void)showUpdateFoundWithAppcastItem:(SUAppcastItem *)item state:(SPUUserUpdateState *)state reply:(void (^)(SPUUserUpdateChoice))reply {
    record(@"found signed update"); reply(SPUUserUpdateChoiceInstall);
}
- (void)showUpdateReleaseNotesWithDownloadData:(SPUDownloadData *)data {}
- (void)showUpdateReleaseNotesFailedToDownloadWithError:(NSError *)error {}
- (void)showUpdateNotFoundWithError:(NSError *)error acknowledgement:(void (^)(void))ack {
    record([@"ERROR no update " stringByAppendingString:error.description]); ack(); exit(4);
}
- (void)showUpdaterError:(NSError *)error acknowledgement:(void (^)(void))ack {
    record([@"ERROR " stringByAppendingString:error.description]); ack(); exit(5);
}
- (void)showDownloadInitiatedWithCancellation:(void (^)(void))cancellation { record(@"downloading"); }
- (void)showDownloadDidReceiveExpectedContentLength:(uint64_t)length {}
- (void)showDownloadDidReceiveDataOfLength:(uint64_t)length {}
- (void)showDownloadDidStartExtractingUpdate { record(@"verified; extracting"); }
- (void)showExtractionReceivedProgress:(double)progress {}
- (void)showReadyToInstallAndRelaunch:(void (^)(SPUUserUpdateChoice))reply {
    self.accepted = YES;
    record(@"ready; install accepted by test driver"); reply(SPUUserUpdateChoiceInstall);
}
- (void)showInstallingUpdateWithApplicationTerminated:(BOOL)terminated retryTerminatingApplication:(void (^)(void))retry {
    record(@"installing");
}
- (void)showUpdateInstalledAndRelaunched:(BOOL)relaunched acknowledgement:(void (^)(void))ack {
    record(@"installed"); ack();
}
- (void)dismissUpdateInstallation {
    record(@"dismissed");
    // The probe deliberately disables relaunch. Sparkle then installs on quit;
    // finish the disposable host normally instead of waiting for its timeout.
    if (self.accepted) dispatch_async(dispatch_get_main_queue(), ^{ [NSApp terminate:nil]; });
}
@end

int main() {
    @autoreleasepool {
        NSApplication *app = NSApplication.sharedApplication;
        [app setActivationPolicy:NSApplicationActivationPolicyProhibited];
        UpdateProbe *delegate = [UpdateProbe new];
        app.delegate = delegate;
        dispatch_after(dispatch_time(DISPATCH_TIME_NOW, 120 * NSEC_PER_SEC), dispatch_get_main_queue(), ^{
            record(@"ERROR integration probe timed out"); exit(6);
        });
        [app run];
    }
    return 0;
}
