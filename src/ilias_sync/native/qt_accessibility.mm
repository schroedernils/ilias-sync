// SPDX-License-Identifier: GPL-3.0-or-later
// Qt 6.10 Cocoa bridge compatibility: native placeholders borrow their parent
// interface ID. Native element teardown must not delete Qt-owned interfaces.
// This mirrors qtbase/dev qcocoaaccessibilityelement.mm's ownership correction.
#import <AppKit/AppKit.h>
#import <Foundation/Foundation.h>
#import <objc/message.h>
#import <objc/runtime.h>

static Class elementClass;
static Ivar rowsIvar;
static Ivar columnsIvar;

static void keepQtOwnedInterfaces(id, SEL, NSArray *) {}

static void releaseNativeElement(id element, SEL selector)
{
    id rows = object_getIvar(element, rowsIvar);
    id columns = object_getIvar(element, columnsIvar);
    [rows release];
    [columns release];
    struct objc_super superclass = {element, class_getSuperclass(elementClass)};
    reinterpret_cast<void (*)(struct objc_super *, SEL)>(objc_msgSendSuper)(&superclass, selector);
}

extern "C" int ilias_set_window_appearance(void *nativeView, int dark)
{
    @autoreleasepool {
        if (!nativeView)
            return 0;
        NSWindow *window = ((NSView *)nativeView).window;
        if (!window)
            return 0;
        NSAppearanceName name = dark ? NSAppearanceNameDarkAqua : NSAppearanceNameAqua;
        if (![window.appearance.name isEqualToString:name])
            window.appearance = [NSAppearance appearanceNamed:name];
        return 1;
    }
}

static NSView *labeled(NSView *host, NSString *name)
{
    for (NSView *subview in host.subviews) {
        if ([subview.identifier isEqualToString:name])
            return subview;
    }
    return nil;
}

extern "C" int ilias_blur_window(void *nativeView, int red, int green, int blue)
{
    @autoreleasepool {
        if (!nativeView)
            return 0;
        NSView *qtView = (NSView *)nativeView;
        NSWindow *window = qtView.window;
        if (!window)
            return 0;
        BOOL dark = (red * 0.2126 + green * 0.7152 + blue * 0.0722) < 140;
        ilias_set_window_appearance(nativeView, dark);
        window.opaque = NO;
        window.backgroundColor = [NSColor clearColor];
        window.titlebarAppearsTransparent = YES;
        window.titleVisibility = NSWindowTitleHidden;
        if (!(window.styleMask & NSWindowStyleMaskFullSizeContentView))
            window.styleMask = window.styleMask | NSWindowStyleMaskFullSizeContentView;
        // Keep Qt's view in place. A child of it paints over the interface, so the
        // wash sits beside it, in the frame behind the content.
        NSView *host = qtView.superview;
        if (!host)
            return 0;
        NSRect area = [host convertRect:qtView.bounds fromView:qtView];
        NSVisualEffectView *blur = (NSVisualEffectView *)labeled(host, @"ilias-blur");
        if (!blur) {
            blur = [[NSVisualEffectView alloc] initWithFrame:area];
            blur.identifier = @"ilias-blur";
            blur.autoresizingMask = NSViewWidthSizable | NSViewHeightSizable;
            blur.blendingMode = NSVisualEffectBlendingModeBehindWindow;
            blur.state = NSVisualEffectStateActive;
            blur.wantsLayer = YES;
            [host addSubview:blur positioned:NSWindowBelow relativeTo:qtView];
            [blur release];
        }
        blur.frame = area;
        blur.material = dark ? NSVisualEffectMaterialHUDWindow : NSVisualEffectMaterialMenu;
        // The stock backdrop is a coarse sample. A wider radius turns it into a smooth wash.
        @try {
            [blur setValue:@(52) forKey:@"blurRadius"];
        } @catch (NSException *exception) {
        }
        NSView *tint = labeled(host, @"ilias-tint");
        if (!tint) {
            tint = [[NSView alloc] initWithFrame:area];
            tint.identifier = @"ilias-tint";
            tint.autoresizingMask = NSViewWidthSizable | NSViewHeightSizable;
            tint.wantsLayer = YES;
            [host addSubview:tint positioned:NSWindowAbove relativeTo:blur];
            [tint release];
        }
        tint.frame = area;
        CGColorRef fill = CGColorCreateGenericRGB(red / 255.0, green / 255.0, blue / 255.0, dark ? 0.58 : 0.66);
        tint.layer.backgroundColor = fill;
        CGColorRelease(fill);
        [host addSubview:qtView positioned:NSWindowAbove relativeTo:tint];
        qtView.wantsLayer = YES;
        qtView.layer.opaque = NO;
        return 1;
    }
}

extern "C" int ilias_fix_qt_accessibility()
{
    static bool installed = false;
    if (installed)
        return 1;
    elementClass = objc_getClass("QMacAccessibilityElement");
    if (!elementClass)
        return 0;
    rowsIvar = class_getInstanceVariable(elementClass, "rows");
    columnsIvar = class_getInstanceVariable(elementClass, "columns");
    Method cleanup = class_getClassMethod(elementClass, @selector(removeElementsFromCache:));
    Method teardown = class_getInstanceMethod(elementClass, sel_registerName("dealloc"));
    // Refuse a changed ABI rather than applying this to an unrelated runtime.
    if (!rowsIvar || !columnsIvar || !cleanup || !teardown
        || ivar_getTypeEncoding(rowsIvar)[0] != '@'
        || ivar_getTypeEncoding(columnsIvar)[0] != '@')
        return 0;
    method_setImplementation(cleanup, reinterpret_cast<IMP>(keepQtOwnedInterfaces));
    method_setImplementation(teardown, reinterpret_cast<IMP>(releaseNativeElement));
    installed = true;
    return 1;
}
