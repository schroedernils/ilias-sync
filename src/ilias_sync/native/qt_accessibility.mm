// SPDX-License-Identifier: GPL-3.0-or-later
// Qt 6.10 Cocoa bridge compatibility: native placeholders borrow their parent
// interface ID. Native element teardown must not delete Qt-owned interfaces.
// This mirrors qtbase/dev qcocoaaccessibilityelement.mm's ownership correction.
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
