/*****************************************************************************

  Copyright (c) 1996-2003 Zope Foundation and Contributors.
  All Rights Reserved.

  This software is subject to the provisions of the Zope Public License,
  Version 2.1 (ZPL).  A copy of the ZPL should accompany this distribution.
  THIS SOFTWARE IS PROVIDED "AS IS" AND ANY AND ALL EXPRESS OR IMPLIED
  WARRANTIES ARE DISCLAIMED, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
  WARRANTIES OF TITLE, MERCHANTABILITY, AGAINST INFRINGEMENT, AND FITNESS
  FOR A PARTICULAR PURPOSE

 ****************************************************************************/

#include "ExtensionClass/ExtensionClass.h"
#include "ExtensionClass/_compat.h"

#define _IN_ACQUISITION_C
#include "Acquisition/Acquisition.h"

static ACQUISITIONCAPI AcquisitionCAPI;

#define ASSIGN(dst, src) Py_XSETREF(dst, src)
#define OBJECT(O) ((PyObject*)(O))

/* sizeof("x") == 2 because of the '\0' byte. */
#define STR_STARTSWITH(ob, pattern) ((strncmp(ob, pattern, sizeof(pattern) - 1) == 0))
#define STR_EQ(ob, pattern) ((strcmp(ob, pattern) == 0))

static PyObject *py__add__, *py__sub__, *py__mul__, *py__div__,
  *py__mod__, *py__pow__, *py__divmod__, *py__lshift__, *py__rshift__,
  *py__and__, *py__or__, *py__xor__, *py__coerce__, *py__neg__,
  *py__pos__, *py__abs__, *py__nonzero__, *py__invert__, *py__int__,
  *py__long__, *py__float__, *py__oct__, *py__hex__,
  *py__getitem__, *py__setitem__, *py__delitem__,
  *py__getslice__, *py__setslice__, *py__delslice__,  *py__contains__,
  *py__len__, *py__of__, *py__call__, *py__repr__,
  *py__str__, *py__unicode__, *py__bytes__,
  *py__cmp__, *py__parent__, *py__iter__, *py__bool__, *py__index__, *py__iadd__,
  *py__isub__, *py__imul__, *py__imod__, *py__ipow__, *py__ilshift__, *py__irshift__,
  *py__iand__, *py__ixor__, *py__ior__, *py__floordiv__, *py__truediv__,
  *py__ifloordiv__, *py__itruediv__, *py__matmul__, *py__imatmul__, *py__idiv__;

static PyObject *Acquired = NULL;

static void
init_py_names(void)
{
#define INIT_PY_NAME(N) py ## N = NATIVE_FROM_STRING(#N)
  INIT_PY_NAME(__add__);
  INIT_PY_NAME(__sub__);
  INIT_PY_NAME(__mul__);
  INIT_PY_NAME(__div__);
  INIT_PY_NAME(__mod__);
  INIT_PY_NAME(__pow__);
  INIT_PY_NAME(__divmod__);
  INIT_PY_NAME(__lshift__);
  INIT_PY_NAME(__rshift__);
  INIT_PY_NAME(__and__);
  INIT_PY_NAME(__or__);
  INIT_PY_NAME(__xor__);
  INIT_PY_NAME(__coerce__);
  INIT_PY_NAME(__neg__);
  INIT_PY_NAME(__pos__);
  INIT_PY_NAME(__abs__);
  INIT_PY_NAME(__nonzero__);
  INIT_PY_NAME(__bool__);
  INIT_PY_NAME(__invert__);
  INIT_PY_NAME(__int__);
  INIT_PY_NAME(__long__);
  INIT_PY_NAME(__float__);
  INIT_PY_NAME(__oct__);
  INIT_PY_NAME(__hex__);
  INIT_PY_NAME(__getitem__);
  INIT_PY_NAME(__setitem__);
  INIT_PY_NAME(__delitem__);
  INIT_PY_NAME(__getslice__);
  INIT_PY_NAME(__setslice__);
  INIT_PY_NAME(__delslice__);
  INIT_PY_NAME(__contains__);
  INIT_PY_NAME(__len__);
  INIT_PY_NAME(__of__);
  INIT_PY_NAME(__call__);
  INIT_PY_NAME(__repr__);
  INIT_PY_NAME(__str__);
  INIT_PY_NAME(__unicode__);
  INIT_PY_NAME(__bytes__);
  INIT_PY_NAME(__cmp__);
  INIT_PY_NAME(__parent__);
  INIT_PY_NAME(__iter__);
  INIT_PY_NAME(__index__);
  INIT_PY_NAME(__iadd__);
  INIT_PY_NAME(__isub__);
  INIT_PY_NAME(__imul__);
  INIT_PY_NAME(__imod__);
  INIT_PY_NAME(__ipow__);
  INIT_PY_NAME(__ilshift__);
  INIT_PY_NAME(__irshift__);
  INIT_PY_NAME(__iand__);
  INIT_PY_NAME(__ixor__);
  INIT_PY_NAME(__ior__);
  INIT_PY_NAME(__floordiv__);
  INIT_PY_NAME(__truediv__);
  INIT_PY_NAME(__ifloordiv__);
  INIT_PY_NAME(__itruediv__);
  INIT_PY_NAME(__matmul__);
  INIT_PY_NAME(__imatmul__);
  INIT_PY_NAME(__idiv__);
#undef INIT_PY_NAME
}

static PyObject *
CallMethod(PyObject *self, PyObject *name, PyObject *args, PyObject *kwargs)
{
    PyObject *callable, *result;

    if ((callable = PyObject_GetAttr(self, name)) == NULL) {
        return NULL;
    }

    result = PyObject_Call(callable, args, kwargs);

    Py_DECREF(callable);
    return result;
}

static PyObject *
CallMethodArgs(PyObject *self, PyObject *name, char *format, ...)
{
    va_list args;
    PyObject *py_args, *result;

    va_start(args, format);
    py_args = Py_VaBuildValue(format, args);
    va_end(args);

    if (py_args == NULL) {
        return NULL;
    }

    result = CallMethod(self, name, py_args, NULL);

    Py_DECREF(py_args);
    return result;
}

/* For obscure reasons, we need to use tp_richcompare instead of tp_compare.
 * The comparisons here all most naturally compute a cmp()-like result.
 * This little helper turns that into a bool result for rich comparisons.
 */
static PyObject *
diff_to_bool(int diff, int op)
{
    PyObject *result;
    int istrue;

    switch (op) {
        case Py_EQ: istrue = diff == 0; break;
        case Py_NE: istrue = diff != 0; break;
        case Py_LE: istrue = diff <= 0; break;
        case Py_GE: istrue = diff >= 0; break;
        case Py_LT: istrue = diff < 0; break;
        case Py_GT: istrue = diff > 0; break;
        default:
            assert(! "op unknown");
            istrue = 0; /* To shut up compiler */
    }

    result = istrue ? Py_True : Py_False;
    Py_INCREF(result);
    return result;
}

static PyObject*
convert_name(PyObject *name)
{
#ifdef Py_USING_UNICODE
    if (PyUnicode_Check(name)) {
        name = PyUnicode_AsEncodedString(name, NULL, NULL);
    }
    else
#endif
    if (!PyBytes_Check(name)) {
        PyErr_SetString(PyExc_TypeError, "attribute name must be a string");
        return NULL;
    }
    else {
        Py_INCREF(name);
    }
    return name;
}

/* Returns 1 if the current exception set is AttributeError otherwise 0.
 * On 1 the AttributeError is removed from the global error indicator.
 * On 0 the global error indactor is still set.
 */
static int
swallow_attribute_error(void)
{
    PyObject* error;

    if ((error = PyErr_Occurred()) == NULL) {
        return 0;
    }

    if (PyErr_GivenExceptionMatches(error, PyExc_AttributeError)) {
        PyErr_Clear();
        return 1;
    }

    return 0;
}

/* Declarations for objects of type Wrapper */

typedef struct {
  PyObject_HEAD
  PyObject *obj;
  PyObject *container;
} Wrapper;

static PyExtensionClass Wrappertype, XaqWrappertype;

#define isImplicitWrapper(o) (Py_TYPE(o) == (PyTypeObject*)&Wrappertype)
#define isExplicitWrapper(o) (Py_TYPE(o) == (PyTypeObject*)&XaqWrappertype)

#define isWrapper(o) (isImplicitWrapper(o) || isExplicitWrapper(o))

/* Same as isWrapper but does a check for NULL pointer. */
#define XisWrapper(o) ((o) ? isWrapper(o) : 0)

#define WRAPPER(O) ((Wrapper*)(O))

#define newWrapper(obj, container, Wrappertype) \
    PyObject_CallFunctionObjArgs(OBJECT(Wrappertype), obj, container, NULL)

static char *init_kwlist[] = {"obj", "container", NULL};

static int
Wrapper_init(Wrapper *self, PyObject *args, PyObject *kwargs)
{
    int rc;
    PyObject *obj, *container;

    rc = PyArg_ParseTupleAndKeywords(
            args, kwargs, "OO:__init__", init_kwlist, &obj, &container);

    if (!rc) {
        return -1;
    }

    if (self == WRAPPER(obj)) {
        PyErr_SetString(PyExc_ValueError,
                        "Cannot wrap acquisition wrapper "
                        "in itself (Wrapper__init__)");
        return -1;
    }

    /* Avoid memory leak if __init__ is called multiple times. */
    Py_CLEAR(self->obj);
    Py_CLEAR(self->container);

    Py_INCREF(obj);
    self->obj = obj;

    if (container != Py_None) {
        Py_INCREF(container);
        self->container = container;
    }

    return 0;
}

static PyObject *
Wrapper__new__(PyTypeObject *type, PyObject *args, PyObject *kwargs)
{
    Wrapper *self = WRAPPER(type->tp_alloc(type, 0));
    if (Wrapper_init(self, args, kwargs) == -1) {
        Py_DECREF(self);
        return NULL;
    }

    return OBJECT(self);
}


static int
Wrapper__init__(Wrapper *self, PyObject *args, PyObject *kwargs)
{
    return Wrapper_init(self, args, kwargs);
}

/* ---------------------------------------------------------------- */

/* Creates a new Wrapper object with the values from the old one.
 * Steals a reference from 'ob' (also in the error case).
 * Returns a new reference.
 * Returns NULL on error.
 */
static PyObject *
clone_wrapper(Wrapper *ob)
{
    PyObject *tmp;

    /* Only clone if its shared with others. */
    if (Py_REFCNT(ob) == 1) {
        return (PyObject*) ob;
    }

    tmp = newWrapper(ob->obj, ob->container, Py_TYPE(ob));
    Py_DECREF(ob);
    return tmp;
}

static PyObject *
__of__(PyObject *inst, PyObject *parent)
{
    PyObject *result;
    result = PyObject_CallMethodObjArgs(inst, py__of__, parent, NULL);

    if (XisWrapper(result) && XisWrapper(WRAPPER(result)->container)) {
        while (XisWrapper(WRAPPER(result)->obj) &&
                (WRAPPER(WRAPPER(result)->obj)->container ==
                 WRAPPER(WRAPPER(result)->container)->obj)) {

            /* Copy it, because the result could be shared with others. */
            if ((result = clone_wrapper(WRAPPER(result))) == NULL) {
                return NULL;
            }

            /* Simplify wrapper */
            Py_XINCREF(WRAPPER(WRAPPER(result)->obj)->obj);
            ASSIGN(WRAPPER(result)->obj, WRAPPER(WRAPPER(result)->obj)->obj);
        }
    }

    return result;
}

static PyObject *
apply__of__(PyObject *self, PyObject *inst)
{
    PyObject *r;

    if (!self) {
        r = self;
    } else if (has__of__(self)) {
        r = __of__(self, inst);
        Py_DECREF(self);
    } else {
        r = self;
    }

    return r;
}

static PyObject *
get_inner(PyObject *ob)
{
    if (isWrapper(ob)) {
        while (isWrapper(WRAPPER(ob)->obj)) {
            ob = WRAPPER(ob)->obj;
        }
    }

    return ob;
}

static PyObject *
get_base(PyObject *ob)
{
    while (isWrapper(ob)) {
        ob = WRAPPER(ob)->obj;
    }
    return ob;
}

static PyObject *
Wrapper_descrget(Wrapper *self, PyObject *inst, PyObject *cls)
{
    if (inst == NULL) {
        Py_INCREF(self);
        return OBJECT(self);
    }

    return __of__(OBJECT(self), inst);
}

static int
Wrapper_traverse(Wrapper *self, visitproc visit, void *arg)
{
    Py_VISIT(self->obj);
    Py_VISIT(self->container);
    return 0;
}

static int
Wrapper_clear(Wrapper *self)
{
    Py_CLEAR(self->obj);
    Py_CLEAR(self->container);
    return 0;
}

static void
Wrapper_dealloc(Wrapper *self)
{
    PyObject_GC_UnTrack(OBJECT(self));
    Wrapper_clear(self);
    Py_TYPE(self)->tp_free(OBJECT(self));
}

static PyObject *
Wrapper_special(Wrapper *self, char *name, PyObject *oname)
{

    PyObject *r = NULL;

    switch(*name) {
        case 'b':
            if (STR_EQ(name, "base")) {
                r = get_base(OBJECT(self));
                Py_INCREF(r);
                return r;
            }
            break;

        case 'p':
            if (STR_EQ(name, "parent")) {
                r = self->container ? self->container : Py_None;
                Py_INCREF(r);
                return r;
            }
            break;

        case 's':
            if (STR_EQ(name, "self")) {
                Py_INCREF(self->obj);
                return self->obj;
            }
            break;

        case 'e':
            if (STR_EQ(name, "explicit")) {
                if (isExplicitWrapper(self)) {
                    Py_INCREF(self);
                    return OBJECT(self);
                }

                return newWrapper(self->obj, self->container, &XaqWrappertype);
            }
            break;

        case 'a':
            if (STR_EQ(name, "acquire")) {
                return Py_FindAttr(OBJECT(self), oname);
            }
            break;

        case 'c':
            if (STR_EQ(name, "chain")) {
                if ((r = PyList_New(0)) == NULL) {
                    return NULL;
                }

                while (PyList_Append(r, OBJECT(self)) == 0) {
                    if (isWrapper(self) && self->container) {
                        self = WRAPPER(self->container);
                    } else {
                        return r;
                    }
                }

                Py_DECREF(r);
                return NULL;
            }
            break;

        case 'i':
            if (STR_EQ(name, "inContextOf")) {
                return Py_FindAttr(OBJECT(self), oname);
            } else if (STR_EQ(name, "inner")) {
                r = get_inner(OBJECT(self));
                Py_INCREF(r);
                return r;
            }
            break;

        case 'u':
            if (STR_EQ(name, "uncle")) {
                return NATIVE_FROM_STRING("Bob");
            }
            break;
    }

    return NULL;
}

static int
apply_filter(PyObject *filter, PyObject *inst, PyObject *oname, PyObject *r,
             PyObject *extra, PyObject *orig)
{
    /* Calls the filter, passing arguments.

    Returns 1 if the filter accepts the value, 0 if not, -1 if an
    exception occurred.

    Note the special reference counting rule: This function decrements
    the refcount of 'r' when it returns 0 or -1.  When it returns 1, it
    leaves the refcount unchanged.
    */

    PyObject *py_res;
    int res;

    py_res = PyObject_CallFunctionObjArgs(filter, orig, inst, oname, r, extra, NULL);
    if (py_res == NULL) {
        Py_DECREF(r);
        return -1;
    }

    res = PyObject_IsTrue(py_res);
    Py_DECREF(py_res);

    if (res == 0 || res == -1) {
        Py_DECREF(r);
        return res;
    }

    return 1;
}

static PyObject *
Wrapper_acquire(Wrapper *self, PyObject *oname,
                PyObject *filter, PyObject *extra, PyObject *orig,
                int explicit, int containment);

static PyObject *
Wrapper_findattr_name(Wrapper *self, char* name, PyObject *oname,
                      PyObject *filter, PyObject *extra, PyObject *orig,
                      int sob, int sco, int explicit, int containment);

static PyObject *
Wrapper_findattr(Wrapper *self, PyObject *oname,
                 PyObject *filter, PyObject *extra, PyObject *orig,
                 int sob, int sco, int explicit, int containment)
/*
  Parameters:

  sob
    Search self->obj for the 'oname' attribute

  sco
    Search self->container for the 'oname' attribute

  explicit
    Explicitly acquire 'oname' attribute from container (assumed with
    implicit acquisition wrapper)

  containment
    Use the innermost wrapper ("aq_inner") for looking up the 'oname'
    attribute.
*/
{
    PyObject *tmp, *result;

    if ((tmp = convert_name(oname)) == NULL) {
        return NULL;
    }

    result = Wrapper_findattr_name(self, PyBytes_AS_STRING(tmp), oname, filter,
                                   extra, orig, sob, sco, explicit, containment);
    Py_XDECREF(tmp);
    return result;
}

static PyObject *
Wrapper_findattr_name(Wrapper *self, char* name, PyObject *oname,
                      PyObject *filter, PyObject *extra, PyObject *orig,
                      int sob, int sco, int explicit, int containment)
/*
 Exactly the same as Wrapper_findattr, except that the incoming
 Python name string/unicode object has already been decoded
 into a C string. This helper function lets us more easily manage
 the lifetime of any temporary allocations.

 This function uses Wrapper_acquire, which only takes the original
 oname value, not the decoded value. That function can call back into
 this one (via Wrapper_findattr). Although that may lead to a few
 temporary allocations as we walk through the containment hierarchy,
 it is correct: This function may modify its internal view of the
 `name` value, and if that were propagated up the hierarchy
 the incorrect name may be looked up.
*/
{
    PyObject *r;

    if (STR_STARTSWITH(name, "aq_") || STR_EQ(name, "__parent__")) {
        /* __parent__ is an alias to aq_parent */
        name = STR_EQ(name, "__parent__") ? "parent" : name + 3;

        if ((r = Wrapper_special(self, name, oname))) {
            if (filter) {
                switch(apply_filter(filter, OBJECT(self), oname, r, extra, orig)) {
                    case -1: return NULL;
                    case 1: return r;
                }
            } else {
                return r;
            }
        } else {
            PyErr_Clear();
        }
    } else if (STR_STARTSWITH(name, "__") &&
                    (STR_EQ(name, "__reduce__") ||
                     STR_EQ(name, "__reduce_ex__") ||
                     STR_EQ(name, "__getstate__"))) {

        return PyObject_GenericGetAttr(OBJECT(self), oname);
    }

    /* If we are doing a containment search, then replace self with aq_inner */
    self = containment ? WRAPPER(get_inner(OBJECT(self))) : self;

    if (sob) {
        if (isWrapper(self->obj)) {
            if (self == WRAPPER(self->obj)) {
                PyErr_SetString(PyExc_RuntimeError,
                                "Recursion detected in acquisition wrapper");
                return NULL;
            }

            r = Wrapper_findattr(
                    WRAPPER(self->obj),
                    oname,
                    filter,
                    extra,
                    orig,
                    1,
                    /* Search object container if explicit,
                    or object is implicit acquirer */
                    explicit || isImplicitWrapper(self->obj),
                    explicit,
                    containment);

            if (r) {
                if (PyECMethod_Check(r) && PyECMethod_Self(r) == self->obj) {
                    ASSIGN(r, PyECMethod_New(r, OBJECT(self)));
                }
                return apply__of__(r, OBJECT(self));

            } else if (!swallow_attribute_error()) {
                return NULL;
            }
        }

        /* Deal with mixed __parent__ / aq_parent circles */
        else if (self->container &&
                 isWrapper(self->container) &&
                 WRAPPER(self->container)->container &&
                 self == WRAPPER(WRAPPER(self->container)->container))
        {
            PyErr_SetString(PyExc_RuntimeError,
                            "Recursion detected in acquisition wrapper");
            return NULL;
        }

        /* normal attribute lookup */
        else if ((r = PyObject_GetAttr(self->obj, oname))) {
            if (r == Acquired) {
                Py_DECREF(r);
                return Wrapper_acquire(
                        self, oname, filter, extra, orig, 1, containment);
            }

            if (PyECMethod_Check(r) && PyECMethod_Self(r) == self->obj) {
                ASSIGN(r, PyECMethod_New(r, OBJECT(self)));
            }

            r = apply__of__(r, OBJECT(self));

            if (r && filter) {
                switch(apply_filter(filter, OBJECT(self), oname, r, extra, orig)) {
                    case -1: return NULL;
                    case 1: return r;
                }
            } else {
                return r;
            }
        } else if (!swallow_attribute_error()) {
            return NULL;
        }

        PyErr_Clear();
    }

    /* Lookup has failed, acquire it from parent. */
    if (sco && (*name != '_' || explicit)) {
        return Wrapper_acquire(
                self, oname, filter, extra, orig, explicit, containment);
    }

    PyErr_SetObject(PyExc_AttributeError, oname);
    return NULL;
}

static PyObject *
Wrapper_acquire(
    Wrapper *self,
    PyObject *oname,
    PyObject *filter,
    PyObject *extra,
    PyObject *orig,
    int explicit,
    int containment)
{
    PyObject *r;
    int sob = 1;
    int sco = 1;

    if (!self->container) {
        PyErr_SetObject(PyExc_AttributeError, oname);
        return NULL;
    }

    /* If the container has an acquisition wrapper itself,
     * we'll use Wrapper_findattr to progress further.
     */
    if (isWrapper(self->container)) {
        if (isWrapper(self->obj)) {
            /* Try to optimize search by recognizing repeated
             * objects in path.
             */
            if (WRAPPER(self->obj)->container == WRAPPER(self->container)->container) {
                sco = 0;
            } else if (WRAPPER(self->obj)->container == WRAPPER(self->container)->obj) {
                sob = 0;
            }
        }

        /* Don't search the container when the container of the
         * container is the same object as 'self'.
         */
        if (WRAPPER(self->container)->container == WRAPPER(self)->obj) {
            sco = 0;
            containment = 1;
        }

        r = Wrapper_findattr(WRAPPER(self->container), oname, filter, extra,
                             orig, sob, sco, explicit, containment);

        return apply__of__(r, OBJECT(self));
    }

    /* If the container has a __parent__ pointer, we create an
     * acquisition wrapper for it accordingly.  Then we can proceed
     * with Wrapper_findattr, just as if the container had an
     * acquisition wrapper in the first place (see above).
     */
    else if ((r = PyObject_GetAttr(self->container, py__parent__))) {
        /* Don't search the container when the parent of the parent
         * is the same object as 'self'
         */
        if (r == WRAPPER(self)->obj) {
            sco = 0;
        }
        else if (WRAPPER(r)->obj == WRAPPER(self)->obj) {
            sco = 0;
        }

        ASSIGN(self->container, newWrapper(self->container, r, &Wrappertype));

        /* don't need __parent__ anymore */
        Py_DECREF(r);

        r = Wrapper_findattr(WRAPPER(self->container), oname, filter, extra,
                             orig, sob, sco, explicit, containment);

        /* There's no need to DECREF the wrapper here because it's
         * not stored in self->container, thus 'self' owns its
         * reference now
         */
        return r;
    }

    /* The container is the end of the acquisition chain; if we
     * can't look up the attribute here, we can't look it up at all.
     */
    else {
        /* We need to clean up the AttributeError from the previous
         * getattr (because it has clearly failed).
         */
        if(!swallow_attribute_error()) {
            return NULL;
        }

        if ((r = PyObject_GetAttr(self->container, oname)) == NULL) {
            /* May be AttributeError or some other kind of error */
            return NULL;
        }

        if (r == Acquired) {
            Py_DECREF(r);
        } else if (filter) {
            switch(apply_filter(filter, self->container, oname, r, extra, orig)) {
                case -1: return NULL;
                case 1: return apply__of__(r, OBJECT(self));
            }
        } else {
            return apply__of__(r, OBJECT(self));
        }
    }

    PyErr_SetObject(PyExc_AttributeError, oname);
    return NULL;
}

static PyObject *
Wrapper_getattro(Wrapper *self, PyObject *oname)
{
    return Wrapper_findattr(self, oname, NULL, NULL, NULL, 1, 1, 0, 0);
}

static PyObject *
Xaq_getattro(Wrapper *self, PyObject *oname)
{
    PyObject *tmp, *result;

    if ((tmp = convert_name(oname)) == NULL) {
        return NULL;
    }

    /* Special case backward-compatible acquire method. */
    if (STR_EQ(PyBytes_AS_STRING(tmp), "acquire")) {
        result = Py_FindAttr(OBJECT(self), oname);
    } else {
        result = Wrapper_findattr(self, oname, NULL, NULL, NULL, 1, 0, 0, 0);
    }

    Py_DECREF(tmp);
    return result;
}

static int
Wrapper_setattro(Wrapper *self, PyObject *oname, PyObject *v)
{

    PyObject *tmp = NULL;
    char *name = "";
    int result;

    if ((tmp = convert_name(oname)) == NULL) {
        return -1;
    }

    name = PyBytes_AS_STRING(tmp);

    if (STR_EQ(name, "aq_parent") || STR_EQ(name, "__parent__")) {
        Py_XINCREF(v);
        ASSIGN(self->container, v);
        result = 0;
    } else {
        if (v) {
            result = PyObject_SetAttr(self->obj, oname, get_base(v));
        }
        else {
            result = PyObject_DelAttr(self->obj, oname);
        }
    }

    Py_DECREF(tmp);
    return result;
}

static int
Wrapper_compare(Wrapper *self, PyObject *w)
{

    PyObject *obj, *wobj;
    PyObject *m;
    int r;

    if (OBJECT(self) == w) {
        return 0;
    }

    if ((m = PyObject_GetAttr(OBJECT(self), py__cmp__)) == NULL) {
        PyErr_Clear();

        /* Unwrap self completely -> obj. */
        obj = get_base(OBJECT(self));

        /* Unwrap w completely -> wobj. */
        wobj = get_base(w);

        if (obj == wobj) {
            return 0;
        } else if (obj < w) {
            return -1;
        } else {
            return 1;
        }
    }

    ASSIGN(m, PyObject_CallFunction(m, "O", w));
    if (m == NULL) {
        return -1;
    }

    r = PyLong_AsLong(m);
    Py_DECREF(m);
    return r;
}

static PyObject *
Wrapper_richcompare(Wrapper *self, PyObject *w, int op)
{
    return diff_to_bool(Wrapper_compare(self, w), op);
}

static PyObject *
Wrapper_repr(Wrapper *self)
{
    PyObject *r;

    if ((r = PyObject_GetAttr(OBJECT(self), py__repr__))) {
        ASSIGN(r, PyObject_CallFunction(r, NULL, NULL));
        return r;
    } else {
        PyErr_Clear();
        return PyObject_Repr(self->obj);
    }
}

static PyObject *
Wrapper_str(Wrapper *self)
{
    PyObject *r;

    if ((r = PyObject_GetAttr(OBJECT(self), py__str__))) {
        ASSIGN(r, PyObject_CallFunction(r,NULL,NULL));
        return r;
    } else {
        PyErr_Clear();
        return PyObject_Str(self->obj);
    }
}

static PyObject *
Wrapper_unicode(Wrapper *self)
{
    PyObject *r;

    if ((r = PyObject_GetAttr(OBJECT(self), py__unicode__))) {
        ASSIGN(r, PyObject_CallFunction(r, NULL, NULL));
        return r;
    } else {
        PyErr_Clear();
        return Wrapper_str(self);
    }
}

static PyObject *
Wrapper_bytes(Wrapper *self)
{
    PyObject *r;

    if ((r = PyObject_GetAttr(OBJECT(self), py__bytes__))) {
        ASSIGN(r, PyObject_CallFunction(r, NULL, NULL));
        return r;
    } else {
        PyErr_Clear();
        return PyBytes_FromObject(self->obj);
    }
}

static long
Wrapper_hash(Wrapper *self)
{
    return PyObject_Hash(self->obj);
}

static PyObject *
Wrapper_call(PyObject *self, PyObject *args, PyObject *kw)
{
    return CallMethod(self, py__call__, args, kw);
}

/* Code to handle accessing Wrapper objects as sequence objects */
static Py_ssize_t
Wrapper_length(PyObject* self)
{
    PyObject *result;
    PyObject *callable;
    PyObject *tres;
    Py_ssize_t res;

    callable = PyObject_GetAttr(self, py__len__);
    if (callable == NULL) {
        if (PyErr_ExceptionMatches(PyExc_AttributeError)) {
            /* PyObject_LengthHint in Python3 catches only TypeError.
             * Python2 catches both (type and attribute error)
             */
            PyErr_SetString(PyExc_TypeError, "object has no len()");
        }
        return -1;
    }

    result = PyObject_CallObject(callable, NULL);
    Py_DECREF(callable);

    if (result == NULL) {
        return -1;
    }

    /* PyLong_AsSsize_t can only be called on long objects. */
    tres = PyNumber_Long(result);
    Py_DECREF(result);

    if (tres == NULL) {
        return -1;
    }

    res = PyLong_AsSsize_t(tres);
    Py_DECREF(tres);

    if (res == -1 && PyErr_Occurred()) {
        return -1;
    }

    return res;
}

static PyObject *
Wrapper_add(PyObject *self, PyObject *bb)
{
    return CallMethodArgs(self, py__add__, "(O)", bb);
}

static PyObject *
Wrapper_repeat(PyObject *self, Py_ssize_t n)
{
    return CallMethodArgs(self, py__mul__, "(n)", n);
}

static PyObject *
Wrapper_item(PyObject *self, Py_ssize_t i)
{
    return CallMethodArgs(self, py__getitem__, "(n)", i);
}

static PyObject *
Wrapper_slice(PyObject *self, Py_ssize_t ilow, Py_ssize_t ihigh)
{
    return CallMethodArgs(self, py__getslice__, "(nn)", ilow, ihigh);
}

static int
Wrapper_ass_item(PyObject *self, Py_ssize_t  i, PyObject *v)
{
    if (v) {
        v = CallMethodArgs(self, py__setitem__, "(nO)", i, v);
    } else {
        v = CallMethodArgs(self, py__delitem__, "(n)", i);
    }

    if (v == NULL) {
        return -1;
    }

    Py_DECREF(v);
    return 0;
}

static int
Wrapper_ass_slice(PyObject *self, Py_ssize_t ilow, Py_ssize_t ihigh, PyObject *v)
{
    if (v) {
        v = CallMethodArgs(self, py__setslice__, "(nnO)", ilow, ihigh, v);
    } else {
        v = CallMethodArgs(self, py__delslice__, "(nn)", ilow, ihigh);
    }

    if (v == NULL) {
        return -1;
    }

    Py_DECREF(v);
    return 0;
}

static int
Wrapper_contains(PyObject *self, PyObject *v)
{
    long result;

    if ((v = CallMethodArgs(self, py__contains__, "(O)", v)) == NULL) {
        return -1;
    }

    result = PyLong_AsLong(v);
    Py_DECREF(v);
    return result;
}

/* Support for iteration cannot rely on the internal implementation of
   `PyObject_GetIter`, since the `self` passed into `__iter__` and
   `__getitem__` should be acquisition-wrapped (also see LP 360761): The
   wrapper obviously supports the iterator protocol so simply calling
   `PyObject_GetIter(OBJECT(self))` results in an infinite recursion.
   Instead the base object needs to be checked and the wrapper must only
   be used when actually calling `__getitem__` or setting up a sequence
   iterator. */
static PyObject *
Wrapper_iter(Wrapper *self)
{
  PyObject *obj = self->obj;
  PyObject *res;
  if ((res=PyObject_GetAttr(OBJECT(self),py__iter__))) {
      ASSIGN(res,PyObject_CallFunction(res,NULL,NULL));
      if (res != NULL && !PyIter_Check(res)) {
          PyErr_Format(PyExc_TypeError,
                   "iter() returned non-iterator "
                   "of type '%.100s'",
                   Py_TYPE(res)->tp_name);
          Py_DECREF(res);
          res = NULL;
      }
  } else if (PySequence_Check(obj)) {
      PyErr_Clear();
      ASSIGN(res,PySeqIter_New(OBJECT(self)));
  } else {
      res = PyErr_Format(PyExc_TypeError, "iteration over non-sequence");
  }
  return res;
}

static PySequenceMethods Wrapper_as_sequence = {
    (lenfunc)Wrapper_length,            /*sq_length*/
    Wrapper_add,                        /*sq_concat*/
    (ssizeargfunc)Wrapper_repeat,       /*sq_repeat*/
    (ssizeargfunc)Wrapper_item,         /*sq_item*/
    (ssizessizeargfunc)Wrapper_slice,   /*sq_slice*/
    (ssizeobjargproc)Wrapper_ass_item,  /*sq_ass_item*/
    (ssizessizeobjargproc)Wrapper_ass_slice,    /*sq_ass_slice*/
    (objobjproc)Wrapper_contains,       /*sq_contains*/
};

/* -------------------------------------------------------------- */

/* Code to access Wrapper objects as mappings */


static PyObject *
Wrapper_subscript(PyObject *self, PyObject *key)
{
    return CallMethodArgs(self, py__getitem__, "(O)", key);
}

static int
Wrapper_ass_sub(PyObject *self, PyObject *key, PyObject *v)
{
    if (v) {
        v = CallMethodArgs(self, py__setitem__, "(OO)", key, v);
    } else {
        v = CallMethodArgs(self, py__delitem__, "(O)", key);
    }

    if (v == NULL) {
        return -1;
    }

    Py_DECREF(v);
    return 0;
}

static PyMappingMethods Wrapper_as_mapping = {
    (lenfunc)Wrapper_length,        /*mp_length*/
    (binaryfunc)Wrapper_subscript,  /*mp_subscript*/
    (objobjargproc)Wrapper_ass_sub, /*mp_ass_subscript*/
};

/* -------------------------------------------------------------- */

/* Code to access Wrapper objects as numbers */

#define WRAP_UNARYOP(OPNAME) \
    static PyObject* Wrapper_##OPNAME(PyObject* self) { \
        return PyObject_CallMethodObjArgs(self, py__##OPNAME##__, NULL); \
    }

#define WRAP_BINOP(OPNAME) \
    static PyObject* Wrapper_##OPNAME(PyObject* self, PyObject* o1) { \
        return CallMethodArgs(self, py__##OPNAME##__, "(O)", o1); \
    }

#define WRAP_TERNARYOP(OPNAME) \
    static PyObject* Wrapper_##OPNAME(PyObject* self, PyObject* o1, PyObject* o2) { \
        return CallMethodArgs(self, py__##OPNAME##__, "(OO)", o1, o2); \
    }

WRAP_BINOP(sub);
WRAP_BINOP(mul);
WRAP_BINOP(mod);
WRAP_BINOP(divmod);
WRAP_TERNARYOP(pow);
WRAP_UNARYOP(neg);
WRAP_UNARYOP(pos);
WRAP_UNARYOP(abs);
WRAP_UNARYOP(invert);
WRAP_BINOP(lshift);
WRAP_BINOP(rshift);
WRAP_BINOP(and);
WRAP_BINOP(xor);
WRAP_BINOP(or);

WRAP_UNARYOP(int);
WRAP_UNARYOP(float);

WRAP_BINOP(iadd);
WRAP_BINOP(isub);
WRAP_BINOP(imul);
WRAP_BINOP(imod);
WRAP_TERNARYOP(ipow);
WRAP_BINOP(ilshift);
WRAP_BINOP(irshift);
WRAP_BINOP(iand);
WRAP_BINOP(ixor);
WRAP_BINOP(ior);
WRAP_BINOP(floordiv);
WRAP_BINOP(truediv);
WRAP_BINOP(ifloordiv);
WRAP_BINOP(itruediv);
WRAP_UNARYOP(index);

#if ((PY_MAJOR_VERSION == 3) && (PY_MINOR_VERSION > 4))
WRAP_BINOP(matmul);
WRAP_BINOP(imatmul);
#endif

static int
Wrapper_nonzero(PyObject *self)
{
    int res;
    PyObject* result = NULL;
    PyObject* callable = NULL;

    callable = PyObject_GetAttr(self, py__bool__);

    if (callable == NULL) {
        PyErr_Clear();

        callable = PyObject_GetAttr(self, py__len__);
        if (callable == NULL) {
            PyErr_Clear();
            return 1;
        }
    }

    result = PyObject_CallObject(callable, NULL);
    Py_DECREF(callable);

    if (result == NULL) {
        return -1;
    }

    res = PyObject_IsTrue(result);
    Py_DECREF(result);

    return res;

}


static PyNumberMethods Wrapper_as_number = {
    Wrapper_add,        /* nb_add */
    Wrapper_sub,        /* nb_subtract */
    Wrapper_mul,        /* nb_multiply */
    Wrapper_mod,        /* nb_remainder */
    Wrapper_divmod,     /* nb_divmod */
    Wrapper_pow,        /* nb_power */
    Wrapper_neg,        /* nb_negative */
    Wrapper_pos,        /* nb_positive */
    Wrapper_abs,        /* nb_absolute */
    Wrapper_nonzero,    /* nb_nonzero */
    Wrapper_invert,     /* nb_invert */
    Wrapper_lshift,     /* nb_lshift */
    Wrapper_rshift,     /* nb_rshift */
    Wrapper_and,        /* nb_and */
    Wrapper_xor,        /* nb_xor */
    Wrapper_or,         /* nb_or */
    Wrapper_int,        /* nb_int */
    NULL,
    Wrapper_float,      /* nb_float */
    Wrapper_iadd,       /* nb_inplace_add */
    Wrapper_isub,       /* nb_inplace_subtract */
    Wrapper_imul,       /* nb_inplace_multiply */
    Wrapper_imod,       /* nb_inplace_remainder */
    Wrapper_ipow,       /* nb_inplace_power */
    Wrapper_ilshift,    /* nb_inplace_lshift */
    Wrapper_irshift,    /* nb_inplace_rshift */
    Wrapper_iand,       /* nb_inplace_and */
    Wrapper_ixor,       /* nb_inplace_xor */
    Wrapper_ior,        /* nb_inplace_or */
    Wrapper_floordiv,   /* nb_floor_divide */
    Wrapper_truediv,    /* nb_true_divide */
    Wrapper_ifloordiv,  /* nb_inplace_floor_divide */
    Wrapper_itruediv,   /* nb_inplace_true_divide */
    Wrapper_index,      /* nb_index */

#if ((PY_MAJOR_VERSION == 3) && (PY_MINOR_VERSION > 4))
    Wrapper_matmul,     /* nb_matrix_multiply */
    Wrapper_imatmul,    /* nb_inplace_matrix_multiply */
#endif
};



/* -------------------------------------------------------- */


static char *acquire_args[] = {"object", "name", "filter", "extra", "explicit",
                               "default", "containment", NULL};

static PyObject *
Wrapper_acquire_method(Wrapper *self, PyObject *args, PyObject *kw)
{
    PyObject *name, *filter = NULL, *extra = Py_None;
    PyObject *expl = NULL, *defalt = NULL;
    int explicit = 1;
    int containment = 0;
    PyObject *result;

    if (!PyArg_ParseTupleAndKeywords(args, kw, "O|OOOOi", acquire_args+1,
                                     &name, &filter, &extra, &expl,
                                     &defalt, &containment))
    {
        return NULL;
    }

    if (expl) {
        explicit = PyObject_IsTrue(expl);
    }

    if (filter == Py_None) {
        filter = NULL;
    }

    result = Wrapper_findattr(self, name, filter, extra, OBJECT(self), 1,
                              explicit || isImplicitWrapper(self),
                              explicit, containment);

    if (result == NULL && defalt != NULL) {
        /* as "Python/bltinmodule.c:builtin_getattr" turn
         * only 'AttributeError' into a default value, such
         * that e.g. "ConflictError" and errors raised by the filter
         * are not mapped to the default value.
         */
        if (swallow_attribute_error()) {
            Py_INCREF(defalt);
            result = defalt;
        }
    }

    return result;
}

/* forward declaration so that we can use it in Wrapper_inContextOf */
static PyObject * capi_aq_inContextOf(PyObject *self, PyObject *o, int inner);

static PyObject *
Wrapper_inContextOf(Wrapper *self, PyObject *args)
{
    PyObject *o;
    int inner = 1;
    if (!PyArg_ParseTuple(args, "O|i", &o, &inner)) {
        return NULL;
    }

    return capi_aq_inContextOf(OBJECT(self), o, inner);
}

PyObject *
Wrappers_are_not_picklable(PyObject *wrapper, PyObject *args)
{
    PyErr_SetString(PyExc_TypeError,
                    "Can't pickle objects in acquisition wrappers.");
    return NULL;
}

static PyObject *
Wrapper___getnewargs__(PyObject *self)
{
    return PyTuple_New(0);
}

static struct PyMethodDef Wrapper_methods[] = {
  {"acquire", (PyCFunction)Wrapper_acquire_method,
   METH_VARARGS|METH_KEYWORDS,
   "Get an attribute, acquiring it if necessary"},
  {"aq_acquire", (PyCFunction)Wrapper_acquire_method,
   METH_VARARGS|METH_KEYWORDS,
   "Get an attribute, acquiring it if necessary"},
  {"aq_inContextOf", (PyCFunction)Wrapper_inContextOf, METH_VARARGS,
   "Test whether the object is currently in the context of the argument"},
  {"__getnewargs__", (PyCFunction)Wrapper___getnewargs__, METH_NOARGS,
    "Get arguments to be passed to __new__"},
  {"__getstate__", (PyCFunction)Wrappers_are_not_picklable, METH_VARARGS,
   "Wrappers are not picklable"},
  {"__reduce__", (PyCFunction)Wrappers_are_not_picklable, METH_VARARGS,
   "Wrappers are not picklable"},
  {"__reduce_ex__", (PyCFunction)Wrappers_are_not_picklable, METH_VARARGS,
   "Wrappers are not picklable"},
  {"__unicode__", (PyCFunction)Wrapper_unicode, METH_NOARGS,
   "Unicode"},
  {"__bytes__", (PyCFunction)Wrapper_bytes, METH_NOARGS,
   "Bytes"},
  {NULL,  NULL}
};

static PyExtensionClass Wrappertype = {
    PyVarObject_HEAD_INIT(NULL, 0)
    "Acquisition.ImplicitAcquisitionWrapper",       /* tp_name */
    sizeof(Wrapper),                                /* tp_basicsize */
    0,                                              /* tp_itemsize */
    (destructor)Wrapper_dealloc,                    /* tp_dealloc */
    (printfunc)0,                                   /* tp_print */
    (getattrfunc)0,                                 /* tp_getattr */
    (setattrfunc)0,                                 /* tp_setattr */
    0,                                              /* tp_compare */
    (reprfunc)Wrapper_repr,                         /* tp_repr */
    &Wrapper_as_number,                             /* tp_as_number */
    &Wrapper_as_sequence,                           /* tp_as_sequence */
    &Wrapper_as_mapping,                            /* tp_as_mapping */
    (hashfunc)Wrapper_hash,                         /* tp_hash */
    (ternaryfunc)Wrapper_call,                      /* tp_call */
    (reprfunc)Wrapper_str,                          /* tp_str */
    (getattrofunc)Wrapper_getattro,                 /* tp_getattro */
    (setattrofunc)Wrapper_setattro,                 /* tp_setattro */
    0,                                              /* tp_as_buffer */
    Py_TPFLAGS_DEFAULT | Py_TPFLAGS_BASETYPE |
          Py_TPFLAGS_HAVE_GC | Py_TPFLAGS_HAVE_VERSION_TAG, /* tp_flags */
    "Wrapper object for implicit acquisition",      /* tp_doc */
    (traverseproc)Wrapper_traverse,                 /* tp_traverse */
    (inquiry)Wrapper_clear,                         /* tp_clear */
    (richcmpfunc)Wrapper_richcompare,               /* tp_richcompare */
    0,                                              /* tp_weaklistoffset */
    (getiterfunc)Wrapper_iter,                      /* tp_iter */
    0,                                              /* tp_iternext */
    Wrapper_methods,                                /* tp_methods */
    0,                                              /* tp_members */
    0,                                              /* tp_getset */
    0,                                              /* tp_base */
    0,                                              /* tp_dict */
    (descrgetfunc)Wrapper_descrget,                 /* tp_descr_get */
    0,                                              /* tp_descr_set */
    0,                                              /* tp_dictoffset */
    (initproc)Wrapper__init__,                      /* tp_init */
    0,                                              /* tp_alloc */
    Wrapper__new__                                  /* tp_new */
};

static PyExtensionClass XaqWrappertype = {
    PyVarObject_HEAD_INIT(NULL, 0)
    "Acquisition.ExplicitAcquisitionWrapper",       /*tp_name*/
    sizeof(Wrapper),                                /* tp_basicsize */
    0,                                              /* tp_itemsize */
    (destructor)Wrapper_dealloc,                    /* tp_dealloc */
    (printfunc)0,                                   /* tp_print */
    (getattrfunc)0,                                 /* tp_getattr */
    (setattrfunc)0,                                 /* tp_setattr */
    0,                                              /* tp_compare */
    (reprfunc)Wrapper_repr,                         /* tp_repr */
    &Wrapper_as_number,                             /* tp_as_number */
    &Wrapper_as_sequence,                           /* tp_as_sequence */
    &Wrapper_as_mapping,                            /* tp_as_mapping */
    (hashfunc)Wrapper_hash,                         /* tp_hash */
    (ternaryfunc)Wrapper_call,                      /* tp_call */
    (reprfunc)Wrapper_str,                          /* tp_str */
    (getattrofunc)Xaq_getattro,                     /* tp_getattro */
    (setattrofunc)Wrapper_setattro,                 /* tp_setattro */
    0,                                              /* tp_as_buffer */
    Py_TPFLAGS_DEFAULT | Py_TPFLAGS_BASETYPE |
          Py_TPFLAGS_HAVE_GC | Py_TPFLAGS_HAVE_VERSION_TAG, /* tp_flags */
    "Wrapper object for explicit acquisition",      /* tp_doc */
    (traverseproc)Wrapper_traverse,                 /* tp_traverse */
    (inquiry)Wrapper_clear,                         /* tp_clear */
    (richcmpfunc)Wrapper_richcompare,               /* tp_richcompare */
    0,                                              /* tp_weaklistoffset */
    (getiterfunc)Wrapper_iter,                      /* tp_iter */
    0,                                              /* tp_iternext */
    Wrapper_methods,                                /* tp_methods */
    0,                                              /* tp_members */
    0,                                              /* tp_getset */
    0,                                              /* tp_base */
    0,                                              /* tp_dict */
    (descrgetfunc)Wrapper_descrget,                 /* tp_descr_get */
    0,                                              /* tp_descr_set */
    0,                                              /* tp_dictoffset */
    (initproc)Wrapper__init__,                      /* tp_init */
    0,                                              /* tp_alloc */
    Wrapper__new__                                  /* tp_new */
};

static PyObject *
acquire_of(PyObject *self, PyObject *inst, PyExtensionClass *target)
{
    if (!PyExtensionInstance_Check(inst)) {
        PyErr_SetString(PyExc_TypeError,
                        "attempt to wrap extension method using an object that"
                        " is not an extension class instance.");
        return NULL;
    }

    return newWrapper(self, inst, target);

}

static PyObject *
aq__of__(PyObject *self, PyObject *inst)
{
    return acquire_of(self, inst, &Wrappertype);
}

static PyObject *
xaq__of__(PyObject *self, PyObject *inst)
{
    return acquire_of(self, inst, &XaqWrappertype);
}

static struct PyMethodDef Acquirer_methods[] = {
    {"__of__",(PyCFunction)aq__of__, METH_O,
     "__of__(context) -- return the object in a context"},

    {NULL, NULL}
};

static struct PyMethodDef ExplicitAcquirer_methods[] = {
    {"__of__",(PyCFunction)xaq__of__, METH_O,
     "__of__(context) -- return the object in a context"},

    {NULL, NULL}
};

static PyObject *
capi_aq_acquire(
    PyObject *self,
    PyObject *name,
    PyObject *filter,
    PyObject *extra,
    int explicit,
    PyObject *defalt,
    int containment)
{
    PyObject *result;

    if (filter == Py_None) {
        filter = NULL;
    }

    /* We got a wrapped object, so business as usual */
    if (isWrapper(self)) {
        result = Wrapper_findattr(WRAPPER(self), name, filter, extra,
                                  OBJECT(self), 1,
                                  explicit || isImplicitWrapper(self),
                                  explicit, containment);
    }

    /* Not wrapped; check if we have a __parent__ pointer.  If that's
     * the case, create a wrapper and pretend it's business as usual.
     */
    else if ((result = PyObject_GetAttr(self, py__parent__))) {
        self = newWrapper(self, result, &Wrappertype);

        /* don't need __parent__ anymore */
        Py_DECREF(result);

        result = Wrapper_findattr(WRAPPER(self), name, filter, extra,
                                  OBJECT(self), 1, 1, explicit, containment);

        /* Get rid of temporary wrapper */
        Py_DECREF(self);
    }

    /* No wrapper and no __parent__, so just getattr. */
    else {
        /* Clean up the AttributeError from the previous getattr
         * (because it has clearly failed).
         */
        if (!swallow_attribute_error()) {
            return NULL;
        }

        if (!filter) {
            result = PyObject_GetAttr(self, name);
        } else {
            /* Construct a wrapper so we can use Wrapper_findattr */
            if ((self = newWrapper(self, Py_None, &Wrappertype)) == NULL) {
                return NULL;
            }

            result = Wrapper_findattr(WRAPPER(self), name, filter, extra,
                                      OBJECT(self), 1, 1, explicit, containment);

            /* Get rid of temporary wrapper */
            Py_DECREF(self);
        }
    }

    if (result == NULL && defalt != NULL) {
        /* Python/bltinmodule.c:builtin_getattr turns only 'AttributeError'
         * into a default value.
         */
        if (swallow_attribute_error()) {
            Py_INCREF(defalt);
            result = defalt;
        }
    }

    return result;
}

static PyObject *
module_aq_acquire(PyObject *ignored, PyObject *args, PyObject *kw)
{
    PyObject *self;
    PyObject *name, *filter = NULL, *extra = Py_None;
    PyObject *expl = NULL, *defalt = NULL;
    int explicit = 1, containment = 0;

    if (!PyArg_ParseTupleAndKeywords(args, kw, "OO|OOOOi", acquire_args,
                                     &self, &name, &filter, &extra, &expl,
                                     &defalt, &containment))
    {
        return NULL;
    }

    if (expl) {
        explicit = PyObject_IsTrue(expl);
    }

    return capi_aq_acquire(self, name, filter, extra,
                           explicit, defalt, containment);
}

static PyObject *
capi_aq_get(PyObject *self, PyObject *name, PyObject *defalt, int containment)
{
    PyObject *result;

    result = capi_aq_acquire(self, name, NULL, NULL, 1, defalt, containment);

    if (result == NULL && defalt) {
        PyErr_Clear();
        Py_INCREF(defalt);
        return defalt;
    } else {
        return result;
    }
}

static PyObject *
module_aq_get(PyObject *r, PyObject *args)
{
    PyObject *self, *name, *defalt = NULL;
    int containment = 0;

    if (!PyArg_ParseTuple(args, "OO|Oi", &self, &name, &defalt, &containment)) {
        return NULL;
    }

    return capi_aq_get(self, name, defalt, containment);
}

static int
capi_aq_iswrapper(PyObject *self) {
    return isWrapper(self);
}

static PyObject *
capi_aq_base(PyObject *self)
{
    PyObject *result = get_base(self);
    Py_INCREF(result);
    return result;
}

static PyObject *
module_aq_base(PyObject *ignored, PyObject *self)
{
    return capi_aq_base(self);
}

static PyObject *
capi_aq_parent(PyObject *self)
{
    PyObject *result;

    if (isWrapper(self) && WRAPPER(self)->container) {
        Py_INCREF(WRAPPER(self)->container);
        return WRAPPER(self)->container;
    }
    else if ((result = PyObject_GetAttr(self, py__parent__))) {
        /* We already own the reference to result (PyObject_GetAttr gives
         * it to us), no need to INCREF here.
         */
        return result;
    } else {
        /* We need to clean up the AttributeError from the previous
         * getattr (because it has clearly failed).
         */
        if (!swallow_attribute_error()) {
            return NULL;
        }

        Py_RETURN_NONE;
    }
}

static PyObject *
module_aq_parent(PyObject *ignored, PyObject *self)
{
    return capi_aq_parent(self);
}

static PyObject *
capi_aq_self(PyObject *self)
{
    PyObject *result;

    if (!isWrapper(self)) {
        result = self;
    } else {
        result = WRAPPER(self)->obj;
    }

    Py_INCREF(result);
    return result;
}

static PyObject *
module_aq_self(PyObject *ignored, PyObject *self)
{
    return capi_aq_self(self);
}

static PyObject *
capi_aq_inner(PyObject *self)
{
    self = get_inner(self);
    Py_INCREF(self);
    return self;
}

static PyObject *
module_aq_inner(PyObject *ignored, PyObject *self)
{
    return capi_aq_inner(self);
}

static PyObject *
capi_aq_chain(PyObject *self, int containment)
{
    PyObject *result;

    /* This allows Py_XDECREF at the end.
     * Needed, because the result of PyObject_GetAttr(self, py__parent__) must
     * be kept alive until not needed anymore. It could be that the refcount of
     * its return value is 1 => calling Py_DECREF too early leads to segfault.
     */
    Py_INCREF(self);

    if ((result = PyList_New(0)) == NULL) {
        return NULL;
    }

    while (1) {
        if (isWrapper(self)) {
            if (containment) {
                ASSIGN(self, get_inner(self));
                Py_INCREF(self);
            }

            if (PyList_Append(result, OBJECT(self)) < 0) {
                goto err;
            }

            if (WRAPPER(self)->container) {
                ASSIGN(self, WRAPPER(self)->container);
                Py_INCREF(self);
                continue;
            }
        } else {
            if (PyList_Append(result, self) < 0) {
                goto err;
            }

            ASSIGN(self, PyObject_GetAttr(self, py__parent__));
            if (self) {
                if (self != Py_None) {
                    continue;
                }
            } else if (!swallow_attribute_error()) {
                goto err;
            }
        }
        break;
    }

    Py_XDECREF(self);
    return result;
err:
    Py_XDECREF(self);
    Py_DECREF(result);
    return NULL;
}

static PyObject *
module_aq_chain(PyObject *ignored, PyObject *args)
{
    PyObject *self;
    int containment = 0;

    if (!PyArg_ParseTuple(args, "O|i", &self, &containment)) {
        return NULL;
    }

    return capi_aq_chain(self, containment);
}

static PyObject *
capi_aq_inContextOf(PyObject *self, PyObject *o, int inner)
{
    PyObject *result = Py_False;

    o = get_base(o);

    /* This allows Py_DECREF at the end, if the while loop did nothing. */
    Py_INCREF(self);

    while (1) {
        /* if aq_base(self) is o: return 1 */
        if (get_base(self) == o) {
            result = Py_True;
            break;
        }

        if (inner) {
            ASSIGN(self, capi_aq_inner(self));
            if (self == NULL) {
                return NULL;
            } else if (self == Py_None) {
                result = Py_False;
                break;
            }
        }

        ASSIGN(self, capi_aq_parent(self));
        if (self == NULL) {
            return NULL;
        } else if (self == Py_None) {
            result = Py_False;
            break;
        }
    }

    Py_DECREF(self);
    Py_INCREF(result);
    return result;
}

static PyObject *
module_aq_inContextOf(PyObject *ignored, PyObject *args)
{
    PyObject *self, *o;
    int inner = 1;

    if (!PyArg_ParseTuple(args, "OO|i", &self, &o, &inner)) {
        return NULL;
    }

    return capi_aq_inContextOf(self, o, inner);
}

static struct PyMethodDef methods[] = {
  {"aq_acquire", (PyCFunction)module_aq_acquire, METH_VARARGS|METH_KEYWORDS,
   "aq_acquire(ob, name [, filter, extra, explicit]) -- "
   "Get an attribute, acquiring it if necessary"
  },
  {"aq_get", (PyCFunction)module_aq_get, METH_VARARGS,
   "aq_get(ob, name [, default]) -- "
   "Get an attribute, acquiring it if necessary."
  },
  {"aq_base", (PyCFunction)module_aq_base, METH_O,
   "aq_base(ob) -- Get the object unwrapped"},
  {"aq_parent", (PyCFunction)module_aq_parent, METH_O,
   "aq_parent(ob) -- Get the parent of an object"},
  {"aq_self", (PyCFunction)module_aq_self, METH_O,
   "aq_self(ob) -- Get the object with the outermost wrapper removed"},
  {"aq_inner", (PyCFunction)module_aq_inner, METH_O,
   "aq_inner(ob) -- "
   "Get the object with all but the innermost wrapper removed"},
  {"aq_chain", (PyCFunction)module_aq_chain, METH_VARARGS,
   "aq_chain(ob [, containment]) -- "
   "Get a list of objects in the acquisition environment"},
  {"aq_inContextOf", (PyCFunction)module_aq_inContextOf, METH_VARARGS,
   "aq_inContextOf(base, ob [, inner]) -- "
   "Determine whether the object is in the acquisition context of base."},
  {NULL,	NULL}
};

static struct PyModuleDef moduledef =
{
    PyModuleDef_HEAD_INIT,
    "_Acquisition",                         /* m_name */
    "Provide base classes for acquiring objects",   /* m_doc */
    -1,                                     /* m_size */
    methods,                                /* m_methods */
    NULL,                                   /* m_reload */
    NULL,                                   /* m_traverse */
    NULL,                                   /* m_clear */
    NULL,                                   /* m_free */
};


static PyObject*
module_init(void)
{
    PyObject *m, *d;
    PyObject *api;

    PURE_MIXIN_CLASS(Acquirer,
                     "Base class for objects that implicitly"
                     " acquire attributes from containers\n",
                     Acquirer_methods);

    PURE_MIXIN_CLASS(ExplicitAcquirer,
                     "Base class for objects that explicitly"
                     " acquire attributes from containers\n",
                     ExplicitAcquirer_methods);

    if (!ExtensionClassImported) {
        return NULL;
    }

    Acquired = NATIVE_FROM_STRING("<Special Object Used to Force Acquisition>");
    if (Acquired == NULL) {
        return NULL;
    }

    m = PyModule_Create(&moduledef);
    d = PyModule_GetDict(m);
    init_py_names();
    PyExtensionClass_Export(d,"Acquirer", AcquirerType);
    PyExtensionClass_Export(d,"ImplicitAcquisitionWrapper", Wrappertype);
    PyExtensionClass_Export(d,"ExplicitAcquirer", ExplicitAcquirerType);
    PyExtensionClass_Export(d,"ExplicitAcquisitionWrapper", XaqWrappertype);

    /* Create aliases */
    PyDict_SetItemString(d,"Implicit", OBJECT(&AcquirerType));
    PyDict_SetItemString(d,"Explicit", OBJECT(&ExplicitAcquirerType));
    PyDict_SetItemString(d,"Acquired", Acquired);

    AcquisitionCAPI.AQ_Acquire = capi_aq_acquire;
    AcquisitionCAPI.AQ_Get = capi_aq_get;
    AcquisitionCAPI.AQ_IsWrapper = capi_aq_iswrapper;
    AcquisitionCAPI.AQ_Base = capi_aq_base;
    AcquisitionCAPI.AQ_Parent = capi_aq_parent;
    AcquisitionCAPI.AQ_Self = capi_aq_self;
    AcquisitionCAPI.AQ_Inner = capi_aq_inner;
    AcquisitionCAPI.AQ_Chain = capi_aq_chain;

    api = PyCapsule_New(&AcquisitionCAPI, "Acquisition.AcquisitionCAPI", NULL);

    PyDict_SetItemString(d, "AcquisitionCAPI", api);
    Py_DECREF(api);

    return m;
}

PyMODINIT_FUNC PyInit__Acquisition(void)
{
    return module_init();
}
