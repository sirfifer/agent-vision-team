You are testing Agent Teams hook inheritance for governance.

Your task:

1. Create exactly 2 tasks using TaskCreate:
   a. "Teammate task alpha: write greeting"
   b. "Teammate task beta: write farewell"

2. After creating both tasks, write the word "done" to teammate-tasks-done.txt.

Important: Create both tasks BEFORE writing any files. The governance system will automatically intercept each TaskCreate call and pair it with a review task.

Do not attempt to complete the tasks or write the actual greeting/farewell content. Just create the tasks and write "done" to the marker file.
