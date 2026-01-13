#include "darray.h"

#include <stdio.h>
#include <stdlib.h>
#include <string.h>

// we are hiding this from user
#define DEFAULT_DARRAY_SIZE 10

// definining darray as labeled in header
struct darray {
    char *a;                // array
    unsigned element_size;  // size of data element
    unsigned length;        // Number of elements in array
    unsigned capacity;      // number of elements allocated
};

static int darray_resize(darray *d) {
    char *tmp;

    if (!(tmp = realloc(d->a, 2 * d->capacity * d->element_size))) {
        return -1;
    }

    d->capacity *= 2;
    d->a = tmp;

    return 0;
}

int darray_init(darray **d, unsigned element_size) {
    if (!(*d = malloc(sizeof(**d))) ||
        !((*d)->a = malloc(element_size * DEFAULT_DARRAY_SIZE))) {
        return -1;
    }
    (*d)->element_size = element_size;
    (*d)->length = 0;
    (*d)->capacity = DEFAULT_DARRAY_SIZE;

    return 0;
}

int darray_destroy(darray *d) {
    free(d->a);
    free(d);
    return 0;
}

// adds a new element to array
int darray_add(darray *d, void *v) {
    if (d->capacity == d->length) {
        if (darray_resize(d)) {
            return -1;
        }
    }

    // insert v at index length
    memcpy(d->a + (d->element_size * d->length), v, d->element_size);
    d->length++;
    return 0;
}

// returns ith element
int darray_at(darray *d, unsigned i, void *v) {
    if (i >= d->length) {
        return -1;  // out of bounds
    }
    // copy data into v
    memcpy(v, d->a + (i * d->element_size), d->element_size);
    return 0;
}

// removes ith element, maintains order of elements
int darray_remove(darray *d, unsigned i) {
    if (i >= d->length) {
        return -1;
    }

    // using memmove b/c src and dst overlap
    // dst is element we are removing
    // src is the i + 1th element
    // number of items
    memmove((d->a + (d->element_size * i)),
            (d->a + (d->element_size * (i + 1))),
            ((d->length - i - 1) * d->element_size));
    d->length--;
    return 0;
}

int darray_length(darray *d) { return d->length; }