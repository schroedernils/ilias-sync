// SPDX-License-Identifier: GPL-3.0-or-later
// State-only AppKit regression: these windows are never displayed.
#import <AppKit/AppKit.h>
#include <cstdio>

#define CHECK(condition) do { if (!(condition)) { std::fprintf(stderr, "%s failed\n", #condition); return 1; } } while (0)

extern "C" int ilias_set_window_appearance(void *, int);

int main()
{
    @autoreleasepool {
        [NSApplication sharedApplication];
        [NSApp setActivationPolicy:NSApplicationActivationPolicyProhibited];
        NSAppearance *applicationAppearance = NSApp.appearance;
        CHECK(ilias_set_window_appearance(nullptr, YES) == 0);
        NSView *detached = [[NSView alloc] initWithFrame:NSZeroRect];
        CHECK(ilias_set_window_appearance(detached, YES) == 0);
        [detached release];
        NSWindow *window = [[NSWindow alloc]
            initWithContentRect:NSMakeRect(0, 0, 400, 300)
            styleMask:NSWindowStyleMaskTitled | NSWindowStyleMaskClosable
            backing:NSBackingStoreBuffered defer:NO];
        window.releasedWhenClosed = NO;
        NSView *view = window.contentView;
        NSArray *appearances = @[NSAppearanceNameAqua, NSAppearanceNameDarkAqua];
        const BOOL modes[] = {NO, YES, NO, YES};
        for (BOOL dark : modes) {
            CHECK(ilias_set_window_appearance(view, dark) == 1);
            NSString *expected = dark ? NSAppearanceNameDarkAqua : NSAppearanceNameAqua;
            CHECK([window.appearance.name isEqualToString:expected]);
            CHECK([[view.effectiveAppearance bestMatchFromAppearancesWithNames:
                appearances] isEqualToString:expected]);
            CHECK([[[window standardWindowButton:NSWindowCloseButton].effectiveAppearance
                bestMatchFromAppearancesWithNames:appearances] isEqualToString:expected]);
            CHECK(window.contentView == view);
            CHECK(view.window == window);
            CHECK(!window.visible);
            CHECK(NSApp.appearance == applicationAppearance);
        }
        [window close];
        [window release];
    }
    return 0;
}
