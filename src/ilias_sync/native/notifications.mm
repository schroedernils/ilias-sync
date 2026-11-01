// SPDX-License-Identifier: GPL-3.0-or-later
#import <Foundation/Foundation.h>
#import <UserNotifications/UserNotifications.h>

// Never request authorization in a headless sync worker. The explicit UI
// preference is the only caller allowed to ask; denial remains denial.
extern "C" int ilias_notification_permission(int request)
{
    @autoreleasepool {
        if (![[NSBundle mainBundle] bundleIdentifier]) return -1;
        UNUserNotificationCenter *center = [UNUserNotificationCenter currentNotificationCenter];
        if (request) {
            [center requestAuthorizationWithOptions:UNAuthorizationOptionAlert
                completionHandler:^(BOOL, NSError *) {}];
            return 0;
        }
        __block int result = -1;
        dispatch_semaphore_t done = dispatch_semaphore_create(0);
        [center getNotificationSettingsWithCompletionHandler:^(UNNotificationSettings *settings) {
            switch (settings.authorizationStatus) {
                case UNAuthorizationStatusNotDetermined: result = 0; break;
                case UNAuthorizationStatusDenied: result = 1; break;
                default: result = 2; break;
            }
            dispatch_semaphore_signal(done);
        }];
        if (dispatch_semaphore_wait(done, dispatch_time(DISPATCH_TIME_NOW, NSEC_PER_SEC)) != 0) return -1;
        return result;
    }
}

extern "C" int ilias_notify(const char *title, const char *body, const char *identifier)
{
    @autoreleasepool {
        if (ilias_notification_permission(0) != 2) return 0;
        UNMutableNotificationContent *content = [UNMutableNotificationContent new];
        content.title = [NSString stringWithUTF8String:title];
        content.body = [NSString stringWithUTF8String:body];
        UNNotificationRequest *request = [UNNotificationRequest
            requestWithIdentifier:[NSString stringWithUTF8String:identifier] content:content trigger:nil];
        __block int accepted = 0;
        dispatch_semaphore_t done = dispatch_semaphore_create(0);
        [[UNUserNotificationCenter currentNotificationCenter] addNotificationRequest:request
            withCompletionHandler:^(NSError *error) { accepted = error ? 0 : 1; dispatch_semaphore_signal(done); }];
        if (dispatch_semaphore_wait(done, dispatch_time(DISPATCH_TIME_NOW, NSEC_PER_SEC)) != 0) return 0;
        return accepted;
    }
}
