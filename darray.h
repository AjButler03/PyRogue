#ifndef DARRAY_H
#define DARRAY_H

#ifdef __cplusplus
extern "C" {
#endif

// hiding these from user
struct darray;  // forward reference- lets compiler know there is a type
                // called struct darray
typedef struct darray darray;  // typedef works like it normally does

// static int darray_resize(darray *d); // hidden from user
int darray_init(darray **d, unsigned element_size);
int darray_destroy(darray *d);
int darray_add(darray *d, void *v);
int darray_at(darray *d, unsigned i, void *v);
int darray_remove(darray *d, unsigned i);
int darray_length(darray *d);

#ifdef __cplusplus
}
#endif

#endif