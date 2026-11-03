// SPDX-License-Identifier: GPL-3.0-or-later
#import <Foundation/Foundation.h>
#import <UserNotifications/UserNotifications.h>

// Banners are suppressed while the app is focused unless a delegate asks for
// them. Opt-in has to be able to show a problem alert with the window open.
@interface IliasNotificationDelegate : NSObject <UNUserNotificationCenterDelegate>
@end

@implementation IliasNotificationDelegate
- (void)userNotificationCenter:(UNUserNotificationCenter *)center
       willPresentNotification:(UNNotification *)notification
         withCompletionHandler:(void (^)(UNNotificationPresentationOptions))completionHandler
{
    completionHandler(UNNotificationPresentationOptionBanner | UNNotificationPresentationOptionList | UNNotificationPresentationOptionSound);
}
@end

static void ensureCenter(void)
{
    static IliasNotificationDelegate *delegate;
    static dispatch_once_t once;
    dispatch_once(&once, ^{
        delegate = [IliasNotificationDelegate new];
        [UNUserNotificationCenter currentNotificationCenter].delegate = delegate;
    });
}

// UserNotifications delivers completions on a queue that may be the main
// queue. A semaphore wait on that same thread times out, so the prompt never
// finishes and every later send is reported as unavailable.
static BOOL waitFor(void (^work)(dispatch_block_t done), NSTimeInterval seconds)
{
    if (![NSThread isMainThread]) {
        dispatch_semaphore_t gate = dispatch_semaphore_create(0);
        work(^{ dispatch_semaphore_signal(gate); });
        return dispatch_semaphore_wait(gate, dispatch_time(DISPATCH_TIME_NOW, (int64_t)(seconds * NSEC_PER_SEC))) == 0;
    }
    __block BOOL finished = NO;
    work(^{
        dispatch_async(dispatch_get_main_queue(), ^{ finished = YES; });
    });
    NSDate *deadline = [NSDate dateWithTimeIntervalSinceNow:seconds];
    while (!finished && [deadline timeIntervalSinceNow] > 0)
        [[NSRunLoop currentRunLoop] runMode:NSDefaultRunLoopMode beforeDate:[NSDate dateWithTimeIntervalSinceNow:0.02]];
    return finished;
}

// Never request authorization in a headless sync worker. The explicit UI
// preference is the only caller allowed to ask; denial remains denial.
extern "C" int ilias_notification_permission(int request)
{
    @autoreleasepool {
        if (![[NSBundle mainBundle] bundleIdentifier]) return -1;
        ensureCenter();
        UNUserNotificationCenter *center = [UNUserNotificationCenter currentNotificationCenter];
        __block int result = -1;
        if (request) {
            BOOL done = waitFor(^(dispatch_block_t finish) {
                [center requestAuthorizationWithOptions:(UNAuthorizationOptionAlert | UNAuthorizationOptionSound)
                    completionHandler:^(BOOL granted, NSError *error) {
                        result = error ? -1 : (granted ? 2 : 1);
                        finish();
                    }];
            }, 120);
            return done ? result : 0;
        }
        BOOL done = waitFor(^(dispatch_block_t finish) {
            [center getNotificationSettingsWithCompletionHandler:^(UNNotificationSettings *settings) {
                switch (settings.authorizationStatus) {
                    case UNAuthorizationStatusNotDetermined: result = 0; break;
                    case UNAuthorizationStatusDenied: result = 1; break;
                    default: result = 2; break;
                }
                finish();
            }];
        }, 3);
        return done ? result : -1;
    }
}

extern "C" int ilias_notify(const char *title, const char *body, const char *identifier)
{
    @autoreleasepool {
        if (!title || !body || !identifier) return 0;
        if (ilias_notification_permission(0) != 2) return 0;
        UNMutableNotificationContent *content = [UNMutableNotificationContent new];
        content.title = [NSString stringWithUTF8String:title];
        content.body = [NSString stringWithUTF8String:body];
        UNNotificationRequest *request = [UNNotificationRequest
            requestWithIdentifier:[NSString stringWithUTF8String:identifier] content:content trigger:nil];
        __block int accepted = 0;
        BOOL done = waitFor(^(dispatch_block_t finish) {
            [[UNUserNotificationCenter currentNotificationCenter] addNotificationRequest:request
                withCompletionHandler:^(NSError *error) {
                    accepted = error ? 0 : 1;
                    finish();
                }];
        }, 3);
        return done ? accepted : 0;
    }
}
