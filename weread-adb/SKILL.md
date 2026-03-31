---
name: weread-adb
description: Use when the user wants to read a book on WeRead (微信读书) via ADB — opening the app, navigating the bookshelf, selecting a book, and auto-turning pages for a configurable duration
---

# WeRead ADB Book Reader

Read books on 微信读书 (WeRead) via ADB, with configurable auto page-turning.

## Prerequisites

- `adb` installed (`brew install android-platform-tools`)
- Device connected (USB or wireless debugging)
- WeRead app installed: `com.tencent.weread`

## Flow

```
Launch app → Bookshelf → Select book → Auto-turn pages (configurable time)
```

## Step-by-step

### 1. Identify the device

```bash
adb devices
# Use -s <serial> for all commands if multiple devices
```

### 2. Launch WeRead

```bash
adb shell am force-stop com.tencent.weread
adb shell monkey -p com.tencent.weread -c android.intent.category.LAUNCHER 1
sleep 3
```

Cold launch lands on the **bookshelf** by default. If the app resumes into a book reader, tap center screen to show toolbar, then tap the back button:

```bash
# Show toolbar
adb shell input tap $(( WIDTH/2 )) $(( HEIGHT/2 ))
sleep 1
# Back button is resource-id: reader_top_backbutton, content-desc: "返回"
# Use uiautomator to find exact bounds (see Element Discovery below)
```

### 3. Ensure you're on the Bookshelf tab

The bottom tab bar has these resource-ids:
- `home_tab_discover` — 发现
- `home_tab_shelf` — 书架 (default on cold launch)
- `home_tab_timeline` — 有声书
- `home_tab_personal` — 我

Check which is selected:
```bash
adb shell uiautomator dump /sdcard/ui.xml && adb pull /sdcard/ui.xml /tmp/ui.xml
# Look for selected="true" in home_tab_shelf
```

If not on bookshelf, tap it. The top nav also has clickable tabs:
- `home_shelf_book_shelf` — 书架
- `home_shelf_book_inventory` — 书单

### 4. Select a book

Books are displayed in a grid. Find them via uiautomator:

```bash
# Book titles have resource-id: book_grid_item_name
# Book covers have resource-id: book_cover_imageview
# Extract bounds and tap center of desired book's cover
```

To select by name, parse the UI dump:
```bash
sed 's/></>\n</g' /tmp/ui.xml | grep 'book_grid_item_name'
# Returns text="Book Title" ... bounds="[x1,y1][x2,y2]"
# Tap center: ((x1+x2)/2, (y1+y2)/2) but use the cover bounds, not the title
```

If the book isn't visible, scroll down (use screen-relative coordinates):
```bash
# Scroll down: swipe from 75% to 25% of screen height, centered horizontally
adb shell input swipe $((WIDTH/2)) $((HEIGHT*3/4)) $((WIDTH/2)) $((HEIGHT/4)) 500
```

### 5. Verify book opened

After tapping a book cover, wait for it to load then confirm you're in the reader:
```bash
sleep 3
adb shell uiautomator dump /sdcard/ui.xml && adb pull /sdcard/ui.xml /tmp/ui.xml
# Check for reader elements: book_page, reader_top_backbutton, or page content in content-desc
sed 's/></>\n</g' /tmp/ui.xml | grep -E 'book_page|reader_top_backbutton'
```

### 6. Auto-turn pages

Page turning = swipe left. Use screen width to calculate swipe coordinates:

```bash
# Get screen dimensions
adb shell wm size  # e.g., "Physical size: 600x800"

# Swipe left (75% → 25% of width, at vertical center)
adb shell input swipe $((WIDTH*3/4)) $((HEIGHT/2)) $((WIDTH/4)) $((HEIGHT/2)) 300
```

**Loop pattern** — turn N pages per minute for M minutes:

```bash
# 5 pages per batch, 1 second between swipes
for i in 1 2 3 4 5; do
  adb shell input swipe 450 400 150 400 300
  sleep 1
done
```

Use `/loop` to schedule recurring page turns:
```
/loop 1m <swipe command for 5 pages>
```

To stop after a set time, use `CronDelete` with the job ID.

### 7. Take screenshots / check progress

```bash
adb shell screencap -p /sdcard/screenshot.png && adb pull /sdcard/screenshot.png /tmp/weread.png
```

The page position indicator (e.g., "55 / 3116") appears at the bottom-right of the reader view.

## Element Discovery

**Always use `uiautomator dump` for reliable coordinates.** Screen sizes vary across devices, so hardcoded coordinates won't work universally.

```bash
adb shell uiautomator dump /sdcard/ui.xml && adb pull /sdcard/ui.xml /tmp/ui.xml
sed 's/></>\n</g' /tmp/ui.xml | grep 'SEARCH_TERM'
```

### Key resource-ids

| Screen | Element | resource-id | content-desc |
|--------|---------|-------------|-------------|
| Reader | Back button | `reader_top_backbutton` | 返回 |
| Reader | Toolbar hint | — | 上滑显示工具栏 |
| Reader | Chapter/TOC | `reader_chapter` | 目录 |
| Reader | Progress | `reader_progress` | 进度 |
| Home | Search bar | `home_shelf_search_bar` | 搜索栏 |
| Home | Bookshelf tab (top) | `home_shelf_book_shelf` | — |
| Home | Book title | `book_grid_item_name` | — |
| Home | Book cover | `book_cover_imageview` | — |
| Home | Bottom: Bookshelf | `home_tab_shelf` | — |
| Home | Bottom: Discover | `home_tab_discover` | — |
| Home | Bottom: Me | `home_tab_personal` | — |

### Bounds → tap coordinates

Parse bounds `[x1,y1][x2,y2]` → tap center `((x1+x2)/2, (y1+y2)/2)`.

## Common Issues

- **App resumes into reader**: Tap center to show toolbar, then tap `reader_top_backbutton` to return to bookshelf
- **Multiple ADB devices**: Always use `adb -s <serial>` for every command
- **Screen turns off**: Run `adb shell input keyevent KEYCODE_WAKEUP` before operations, or set long timeout: `adb shell settings put system screen_off_timeout 1800000`
- **Book not visible on shelf**: Scroll down with `adb shell input swipe 300 600 300 200 500`
- **Coordinates wrong**: Never hardcode — always use `uiautomator dump` to find current bounds
