# Step A: Start with a basic Linux system that has Python 3.11 installed.
FROM python:3.11-slim-bullseye

# Step B: Inside that Linux system, create a folder named "app" and make it our workplace.
WORKDIR /app

# Step C: Copy just ONE file from your computer into the "app" folder inside the container.
# We do this one first because it changes infrequently. Docker is smart and will skip
# re-installing everything later if this file hasn't changed.
COPY requirements.txt .

# Step D: Inside the container, run the command 'pip install' using the file we just copied.
# This installs streamlit, pyperclip, etc. inside our private Linux environment.
RUN pip install --no-cache-dir -r requirements.txt

# Step E: Now, copy EVERYTHING ELSE from your project folder (your .py scripts, the assets folder)
# into the "app" folder inside the container.
COPY . .

# Step F: Announce that the application inside this container will listen on port 8501.
# This is like opening a window on a house so people can talk to it.
EXPOSE 8501

# Step G: This is the final command to run when the container starts.
# It tells Streamlit to run your app and, VERY IMPORTANTLY, to listen for
# connections from ANYWHERE (0.0.0.0), not just from inside the container itself.
CMD ["streamlit", "run", "_1streamlit-app-duplicate_finder.py", "--server.address=0.0.0.0"]
