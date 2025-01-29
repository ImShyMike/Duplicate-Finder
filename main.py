"""Main application file for the duplicate scanner."""

import hashlib
import os
import tkinter as tk
from tkinter import filedialog

import dearpygui.dearpygui as dpg
import xxhash


def open_directory_selector():
    """Open a native directory selection dialog."""
    # Hide the tkinter root window
    root = tk.Tk()
    root.withdraw()

    # Open the directory selector dialog
    directory_path = filedialog.askdirectory()

    if directory_path:
        dpg.set_value("directory_text", f"{directory_path}")


def handle_resize(_, __):
    """Callback to handle viewport resizing."""
    width, height = dpg.get_viewport_client_width(), dpg.get_viewport_client_height()

    # Adjust the main window size to match the viewport
    dpg.set_item_width("__main_window", width)
    dpg.set_item_height("__main_window", height)


def xxhashsum(filename, algo="xxh128"):
    """Hash the contents of a file using the xxhash algorithm."""
    if algo not in xxhash.algorithms_available:
        raise NotImplementedError
    digest = getattr(xxhash, algo)
    with open(filename, "rb", buffering=0) as f:
        return hashlib.file_digest(f, digest).hexdigest()


def xxprehashsum(filename, algo="xxh128", size=8**6):  # 256KB
    """Hash the first `size` bytes of a file using the xxhash algorithm."""
    if algo not in xxhash.algorithms_available:
        raise NotImplementedError
    digest = getattr(xxhash, algo)
    with open(filename, "rb", buffering=0) as f:
        return digest(f.read(size)).hexdigest()


def format_filesize(size):
    """Format the file size in human-readable format."""
    if size < 1024:
        return f"{size} B"
    if size < 1024**2:
        return f"{size / 1024:.2f} KB"
    if size < 1024**3:
        return f"{size / 1024**2:.2f} MB"
    if size < 1024**4:
        return f"{size / 1024**3:.2f} GB"
    return f"{size / 1024**4:.2f} TB"


def scan_directory():
    """Scan the selected directory and display the contents."""

    directory_path = dpg.get_value("directory_text").replace("Selected Directory: ", "")
    if (
        not directory_path
        or directory_path == "No directory selected."
        or not os.path.isdir(directory_path)
    ):
        print("Invalid directory path.")
        return

    # Clear the existing table if it exists
    if dpg.does_item_exist("directory_contents"):
        dpg.delete_item("directory_contents")

    hashes = {}
    duplicates = {}

    # Create a new table to display directory contents
    with dpg.child_window(
        width=-1, height=-1, parent="__main_window", tag="directory_contents"
    ):
        # Count total files for progress tracking
        dpg.add_text("Indexing files...", tag="scanning_text")
        total_files = sum(len(files) for _, _, files in os.walk(directory_path))
        processed_files = 0
        dpg.delete_item("scanning_text")

        # Create a progress bar
        progress_bar_tag = dpg.add_progress_bar(width=-1, label="Scanning...")
        progress_text_tag = dpg.add_text(f"Processed: {processed_files}/{total_files}")

        # Walk through the directory and calculate the hash of each file
        for root, _, files in os.walk(directory_path):
            for file in files:
                filehash = xxprehashsum(os.path.join(root, file))
                relative_path = os.path.relpath(
                    os.path.join(root, file), directory_path
                )
                if filehash in hashes:
                    # Calculate the relative path
                    duplicates[filehash] = duplicates.get(filehash, []) + [
                        relative_path
                    ]
                else:
                    hashes[filehash] = relative_path

                # Refresh the screen
                processed_files += 1
                progress_percentage = processed_files / total_files
                dpg.set_value(progress_bar_tag, progress_percentage)
                dpg.set_value(
                    progress_text_tag,
                    f"Processed: {processed_files}/{total_files}",
                )

        # Recheck with full hash
        dpg.add_text("Rechecking duplicates...", tag="rechecking_text")
        true_duplicates = {}
        for filehash, paths in duplicates.items():
            if filehash not in hashes:
                continue

            all_paths = [
                os.path.join(directory_path, path)
                for path in paths + [hashes[filehash]]
            ]

            # Get full hash for first file
            first_path = all_paths[0]
            full_hash = xxhashsum(first_path)
            matches = [first_path]

            # Compare other files against full hash
            for path in all_paths[1:]:
                if xxhashsum(path) == full_hash:
                    matches.append(path)

            if len(matches) > 1:  # Only store if actual duplicates found
                true_duplicates[full_hash] = matches

        dpg.delete_item("rechecking_text")

        # Sort duplicates by file size
        file_sizes = {
            filehash: os.path.getsize(
                os.path.join(directory_path, true_duplicates[filehash][0])
            )
            for filehash in true_duplicates
        }
        sorted_duplicates = sorted(
            true_duplicates.items(), key=lambda item: file_sizes[item[0]], reverse=True
        )

        # Display found duplicates in a table
        dpg.set_value(progress_text_tag, f"Processed: {total_files} files")
        with dpg.table(header_row=True, scrollX=True, scrollY=True):
            dpg.add_table_column(label="File Size", width=10, width_fixed=True)
            dpg.add_table_column(label="File Paths")
            # dpg.add_table_column(label="Duplicate File Hash", width=10, width_fixed=True)

            # Populate the table with relative file paths and additional file info
            for filehash, paths in sorted_duplicates:
                file_size = file_sizes[filehash]

                if file_size == 0:
                    continue  # Skip zero-byte files

                with dpg.table_row():
                    dpg.add_text(format_filesize(file_size))  # Display file size in KB
                    dpg.add_text(
                        ", ".join(
                            [os.path.basename(path) for path in paths]
                        ),  # Display the first 24 characters of each path
                        tag=filehash,
                    )
                    # dpg.add_text(filehash)

                    with dpg.tooltip(filehash):
                        dpg.add_text("\n".join(paths))

        # Remove the progress bar
        dpg.delete_item(progress_bar_tag)


def main():
    """Entrypoint function."""
    with dpg.window(
        label="Duplicate File Scanner",
        width=784,
        height=761,
        pos=(0, 0),
        no_title_bar=True,
        no_resize=True,
        no_move=True,
        no_close=True,
        tag="__main_window",
    ):
        # Add a button to open the directory selector
        dpg.add_button(label="Select Directory", callback=open_directory_selector)

        # Add a text widget to display the selected directory
        dpg.add_text("Selected Directory:", tag="directory_label")
        dpg.add_text("No directory selected.", tag="directory_text")

        dpg.add_button(label="Scan", callback=scan_directory)


if __name__ == "__main__":
    dpg.create_context()
    dpg.create_viewport(
        title="Duplicate File Scanner",
        width=800,
        height=800,
        decorated=True,
        min_width=600,
        min_height=600,
    )

    # Register a callback to handle resizing
    dpg.set_viewport_resize_callback(handle_resize)

    main()

    dpg.setup_dearpygui()
    dpg.show_viewport()
    dpg.start_dearpygui()
    dpg.destroy_context()
