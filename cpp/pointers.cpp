
//Pointers.cpp Example:This program demonstrates the use of pointers in C++
//It declares an integer variable x and a pointer p that points to x
//It then prints the value of x, the memory address of x, the value of x using the pointer, and the memory address of x using the pointer
//The output will be the value of x, the memory address of x, the value of x using the pointer, and the memory address of x using the pointer
//The value of x is: 5
//The memory address of x is: 0x7fffbf7b1bfc
//The value of x using the pointer is: 5
//The memory address of x using the pointer is: 0x7fffbf7b1bfc
//The memory address of x and the memory address of x using the pointer are the same
//This demonstrates that the pointer is pointing to the memory address of x

#include <iostream>
using namespace std;
	
	int main()
{
	int x = 5;
	int *p = &x;
	
	cout << "The value of x is: " << x << endl;
	cout << "The memory address of x is: " << &x << endl;
	cout << "The value of x using the pointer is: " << *p << endl;
	cout << "The memory address of x using the pointer is: " << p << endl;
	
	return 0;
}
//This is the end
