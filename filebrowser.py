import flet as ft
import asyncio
import pprint
from bosesoundtouchapi.models import Navigate

# Configuration
SOURCE = "STORED_MUSIC"


def create_filebrowser(client, accountid, saved_path, on_close, page):
    current_items = []
    path_stack = saved_path

    # UI Components
    file_list = ft.Column([], spacing=5, scroll="auto")

    path_display = ft.Text(
        "",
        size=12,
        color=ft.Colors.GREY_400,
    )

    back_button = ft.ElevatedButton(
        " ← Back ",
        on_click=lambda e: go_back(),
        bgcolor=ft.Colors.GREY_800,
        color=ft.Colors.WHITE,
        disabled=True,
    )

    progress_ring = ft.ProgressRing(width=20, height=20, visible=False)

    def update_path_display():
        if not path_stack:
            path_display.value = "Root"
        else:
            path_display.value = " ⏵ ".join([item.Name for item in path_stack])
        back_button.disabled = len(path_stack) == 0
        if back_button.page:
            back_button.update()
        if path_display.page:
            path_display.update()

    async def browse_folder_async(container_item=None, add_to_stack=True):
        nonlocal current_items

        try:
            if add_to_stack and container_item is not None:
                path_stack.append(container_item)

            nav = Navigate(
                source=SOURCE, sourceAccount=accountid, containerItem=container_item
            )

            progress_ring.visible = True
            progress_ring.update()

            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(
                None, lambda: client.GetMusicLibraryItems(nav)
            )
            current_items = result.Items
            # print("length:", len(current_items))
            # this somehow only loads 1000 items max (?)

            file_list.controls.clear()

            if not current_items:
                file_list.controls.append(
                    ft.Text("(Empty folder)", color=ft.Colors.GREY_400, italic=True)
                )
            else:
                for idx, item in enumerate(current_items):
                    if item.TypeValue == "dir":
                        icon = ft.Icons.FOLDER
                        icon_color = ft.Colors.YELLOW_700
                    elif item.TypeValue == "track":
                        icon = ft.Icons.MUSIC_NOTE
                        icon_color = ft.Colors.BLUE_400
                    else:
                        icon = ft.Icons.AUDIO_FILE_OUTLINED
                        icon_color = ft.Colors.BLUE_300

                    row_content = ft.Row(
                        [
                            # ft.Text(str(idx + 1), color=ft.Colors.WHITE24),
                            ft.Icon(icon, color=icon_color, size=20),
                            ft.Text(
                                item.Name,
                                size=13,
                                color=ft.Colors.WHITE,
                                expand=True,
                            ),
                            ft.IconButton(
                                icon=ft.Icons.PLAY_ARROW,
                                icon_size=20,
                                icon_color=ft.Colors.GREEN_400,
                                data=idx,
                                on_click=lambda e, item=item: handle_item_click(
                                    item, "button"
                                ),
                                padding=ft.padding.symmetric(horizontal=15),
                            ),
                        ],
                        alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                    )

                    item_row = ft.GestureDetector(
                        content=ft.Container(
                            content=row_content,
                            bgcolor=ft.Colors.GREY_800,
                            border_radius=5,
                            padding=ft.padding.symmetric(horizontal=10, vertical=0),
                        ),
                        on_tap=lambda e, item=item: handle_item_click(item, "row"),
                        mouse_cursor=ft.MouseCursor.CLICK,
                    )

                    file_list.controls.append(item_row)

            update_path_display()
            if file_list.page:
                file_list.update()
                file_list.scroll_to(offset=0)

            progress_ring.visible = False
            progress_ring.update()

        except Exception as e:
            print(f"Browse error: {str(e)}")

    def browse_folder(container_item=None, add_to_stack=True):
        page.run_task(browse_folder_async, container_item, add_to_stack)

    def handle_item_click(item, source=None):
        if source == "row" and item.TypeValue == "dir":
            browse_folder(item, add_to_stack=True)
        else:
            play_item(item)  # play folder or track

    def play_item(item):
        print("Playing:", item.ContentItem.Name)
        try:
            msg = client.PlayContentItem(item.ContentItem)
            print("msg:", msg)
        except Exception as e:
            print(f"Play error: {str(e)}")

    def go_back():
        if path_stack:
            path_stack.pop()  # remove current level
            parent_item = path_stack[-1] if path_stack else None
            browse_folder(parent_item, add_to_stack=False)

    # Initialization
    try:
        if not path_stack:
            nav = Navigate(source=SOURCE, sourceAccount=accountid, containerItem=None)
            result = client.GetMusicLibraryItems(nav)
            folder_item = next(
                (item for item in result.Items if item.Name == "Folder"), None
            )
            if folder_item:
                path_stack.append(folder_item)  # add folder to stack
                nav_folder = Navigate(
                    source=SOURCE, sourceAccount=accountid, containerItem=folder_item
                )
                folder_result = client.GetMusicLibraryItems(nav_folder)
                target_item = next(
                    (
                        item
                        for item in folder_result.Items
                        if item.Name == "/mnt/usb1_1"
                    ),
                    None,
                )
                if target_item:
                    browse_folder(target_item, add_to_stack=True)
                else:
                    print("Error: /mnt/usb1_1 not found.")
                    browse_folder(folder_item, add_to_stack=False)
            else:
                print("Error: Folder not found.")
                browse_folder(None, add_to_stack=False)
        else:
            print("File browser restoring last path...")
            current_folder_item = path_stack[-1]
            path_stack.pop()
            browse_folder(current_folder_item, add_to_stack=True)
    except Exception as e:
        print(f"Error loading: {str(e)}")

    update_path_display()

    # Build the UI
    ui = ft.Container(
        content=ft.Column(
            [
                ft.Row(
                    [
                        back_button,
                        progress_ring,
                        ft.IconButton(
                            icon=ft.Icons.CLOSE,
                            icon_color=ft.Colors.WHITE,
                            on_click=on_close,
                        ),
                    ],
                    alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                ),
                # path_display,
                ft.Container(
                    content=file_list,
                    bgcolor=ft.Colors.GREY_900,
                    border_radius=10,
                    padding=5,
                    expand=True,
                    height=400,
                ),
            ],
            spacing=15,
            horizontal_alignment=ft.CrossAxisAlignment.STRETCH,
            expand=True,
        ),
        padding=20,
        expand=True,
    )
    return ui


def main(page: ft.Page):
    page.title = "File Browser"
    page.theme_mode = ft.ThemeMode.DARK
    page.padding = 0

    def close_browser(e, stack=None):
        page.window_close()

    browser = create_filebrowser(None, "account_id", [], close_browser, page)
    page.add(browser)


if __name__ == "__main__":
    ft.app(target=main)
