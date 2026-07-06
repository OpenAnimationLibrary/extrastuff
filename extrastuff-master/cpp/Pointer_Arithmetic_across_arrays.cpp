//Simple exwample of running pointer arithmetic across arrays
//This is an update with no change
//Example:
//This is a new comment
#include <stdio.h>
#include <stdlib.h>

void mergeSortedArrays(int *array1, int size1, int *array2, int size2, int *mergedArray) {
    int *ptr1 = array1; // Pointer to the current element of array1
    int *ptr2 = array2; // Pointer to the current element of array2
    int *end1 = array1 + size1; // Pointer to the end of array1
    int *end2 = array2 + size2; // Pointer to the end of array2
    int *dest = mergedArray; // Pointer to the current element of mergedArray

    while (ptr1 < end1 && ptr2 < end2) {
        if (*ptr1 < *ptr2) {
            *dest++ = *ptr1++; // Copy element and increment pointers
        } else {
            *dest++ = *ptr2++;
        }
    }

    // Copy remaining elements from array1, if any
    while (ptr1 < end1) {
        *dest++ = *ptr1++;
    }

    // Copy remaining elements from array2, if any
    while (ptr2 < end2) {
        *dest++ = *ptr2++;
    }
}

int main() {
    int array1[] = {1, 3, 5};
    int array2[] = {2, 4, 6};
    int size1 = sizeof(array1) / sizeof(array1[0]);
    int size2 = sizeof(array2) / sizeof(array2[0]);
    int *mergedArray = (int *)malloc((size1 + size2) * sizeof(int));

    mergeSortedArrays(array1, size1, array2, size2, mergedArray);

    for (int i = 0; i < size1 + size2; i++) {
        printf("%d ", mergedArray[i]);
    }
    printf("\n");

    free(mergedArray);
    return 0;
}
