# How to Add TypeScript Code

To add your own TypeScript code to Wizarr in ```/static/src/ts/``` to be accessed in the project, you will need to do the following:

1. Create a new file in ```/static/src/ts/``` with your code.

2. Import your function from your module file in ```/static/src/ts/AddToDom.ts```.

Example: 
```
import ScanLibraries from "./ScanLibraries";
```

3. Add your function to the ```modules``` array in ```/static/src/ts/AddToDom.ts```.

Example:
```
onst modules = [ScanLibraries, ...];

```

4. You can now call your function inside Wizarr templates by referencing the ```window``` object.

TIP: You can use the below code to access your function after the page has loaded. Your function won't be available on the ```window``` object until the page has loaded.
```
document.addEventListener("DOMContentLoaded", function(event) { 
    window.ScanLibraries();
});
```