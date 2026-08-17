
# Kemoffu Downloader

A multi-threaded downloader that provides an intuitive GUI for `kemono-dl`.

It allows you to process large numbers of URLs at once and provides extensive control over what to download, including content types, file formats, dates, file sizes, output locations, and file naming patterns.

The actual download process is handled by the `kemono-dl` CLI engine. On top of that, Kemoffu Downloader provides its own task management, in-memory search, responsive visual search, WAF/Turnstile handling, two-stage staging storage, download history, previews, and other GUI-specific features.

> **Note**
>
> This application provides a large number of configuration options.
>
> You can hover your mouse over GUI controls to view detailed tooltips explaining what each option does.
>
> This README focuses on the major features and GUI-specific functionality.

## Features

### ⚡ High-Speed Parallel Downloads

Kemoffu can process multiple download tasks in parallel, significantly reducing the time required compared with the sequential download process of `kemono-dl`.

In our development testing, downloads that could take **more than ten hours** depending on the content and environment were reduced to approximately **15–30 minutes**.

Kemoffu also supports downloading through proxies. Combined with parallel downloads, this has been tested to reach **near the maximum available bandwidth on 400–500 Mbps-class internet connections**.

> ※ Actual download speeds and completion times vary depending on network conditions, the target site, proxy performance, the number of concurrent tasks, file sizes, and other factors.

### 🚀 Download & Task Management

- **Batch URL processing**: Enter multiple URLs, one per line. Drag-and-drop URL input is also supported.
- **Parallel task processing**: Run multiple download processes concurrently with a configurable process count.
- **Favorites batch retrieval**: Automatically expand favorite users and posts from Kemono / Coomer / Pawchive.
- **Real-time progress display**: View per-task progress, transfer speed, ETA, and progress bars.
- **Suspend & Resume**: Safely suspend, resume, or completely stop individual processes.
- **Batch staging**: Download files into a temporary working directory and move them to the final destination after processing is complete.

### 📦 Customizable Download Targets

- **Attachments**: Download the main images, videos, archives, and other attached files.
- **Post content (HTML)**: Save post text as HTML, with support for including comments.
- **Inline images**: Automatically extract and save images embedded in post content.
- **Metadata (JSON)**: Save raw post data returned by the API.
- **Link extraction**: Extract external links from post content or collect links across an entire user.
- **User profiles**: Save profile icons, banners, announcements, Fanbox information, and fan cards.
- **External integration**: Use `yt-dlp` to download embedded videos.

### 🧰 Filters & File Organization

- **Date filters**: Filter posts by publication date or site-added date.
- **User update date filter**: Restrict downloads based on creator information update dates.
- **File size limits**: Specify minimum and maximum file sizes, such as `10mb` or `500kb`.
- **File extension filters**: Specify allowed or excluded file extensions.
- **Keyword filters**: Include or exclude posts based on titles or filenames.
- **Directory & filename patterns**: Dynamically generate directory structures and filenames using variables such as `{service}/{username} [{user_id}]`.

### ⚙️ Networking & Automation

- **Advanced error handling**: Automatically sleep and retry after errors such as `403 Forbidden` and `429 Too Many Requests`.
- **Proxy support**: Supports HTTP, SOCKS4, SOCKS5, and SOCKS5h proxies.
- **Proxy evaluation**: Track proxy error rates and save reports to `proxy_report.txt`.
- **Duplicate prevention & resume support**: Hash verification and `.part` files allow interrupted downloads to be resumed.

### ✨ GUI-Specific Features

- **WAF / Turnstile handling**

  When access to a site is blocked by a security challenge such as Turnstile, the built-in browser can be used to complete the challenge manually. The resulting session cookies can then be captured and applied to subsequent requests so the operation can be retried.

- **Responsive Visual Search**

  The visual search interface automatically adjusts its card layout to the available window width. A **"Next Page"** card can be inserted when there is available space at the end of a page. Failed image requests can also be retried individually according to the configured retry count.

- **In-memory creator search**

  Creator information cached locally can be searched by name or ID without repeatedly querying the remote service. Search results also display per-site result counts.

- **User data isolation (APPDATA)**

  Application data such as `config.json`, `cookies.txt`, `creators_cache.json`, and `archive.txt` is stored separately under the OS-standard user data directory (`%APPDATA%\Kemoffu`) rather than relying on the application's installation directory.

- **Two-stage Staging storage**

  Downloaded files are first written to a temporary working directory and moved to the configured destination after the download process is complete.

- **Kemono / Pawchive Favorites Migration**

  Capture favorite authors and posts from one site through the browser and automatically import them into the other site.

## Requirements & Installation

### 1. Using the packaged `.exe`

- Download the pre-built package from the Releases page.
- **Python is not required.**
- The packaged application is designed to run standalone.

### 2. Running from Python source

- Python 3.9 or later
- Install the required packages:

```bash
pip install -r requirements.txt
````

The requirements file includes dependencies for both Kemoffu Downloader and the bundled `kemono-dl` CLI engine.

If you want to use GUI features that require the built-in browser, such as cookie login, WAF verification, or Favorites Migration, `PyQt6-WebEngine` is also required.

```bash
pip install PyQt6-WebEngine
```

## Basic Usage

### 1. Enter URLs

Enter URLs into the text area at the top of the window, one URL per line.

For example:

```text
https://kemono.cr/patreon/user/12345
```

Creator/user page URLs can be expanded into individual posts and added to the task queue automatically.

URLs can also be added by dragging and dropping them into the input area.

### 2. Configure the download

Switch between the available tabs and configure:

* What content should be downloaded
* Date and file filters
* File naming and directory patterns
* Proxy settings
* Number of parallel processes
* Other advanced options

### 3. Select the destination

The default destination is:

```text
%USERPROFILE%\Downloads\Kemoffu
```

You can enable the option to override the root output directory and select any other destination.

### 4. Start downloading

Click:

**▶ Start Download**

The GUI displays task progress, transfer speed, and logs in real time.

## Advanced Features

### 🌐 WAF / Turnstile Handling

When a request is blocked by a site security challenge such as Turnstile, a confirmation dialog may appear.

1. The target site is opened in the built-in browser.
2. Complete the security challenge manually.
3. Click **"Get Session and Retry"**.
4. The obtained session cookies are retained and automatically applied to subsequent requests.

This allows the interrupted operation to continue without manually restarting the entire task.

### 🎨 Responsive Visual Search

The Visual Search window can be opened using the **"Open Visual Search"** button in the Search tab.

Features include:

* **Dynamic layout**: The number of cards per row is automatically adjusted according to the window width.
* **Next Page card**: A dedicated animated card can be placed at the end of the result grid to navigate to the next page.
* **Individual image retries**: Failed icon or banner image requests can be retried automatically according to the configured retry count.

Search results can also be added directly to the main URL list.

### 💾 Two-stage Staging Storage

When a custom destination is enabled, downloaded files are handled in two stages:

1. Files are downloaded into the temporary working directory:

   ```text
   _temp_staging_batch
   ```

2. After the download tasks are complete, the resulting directory structure is moved to the configured destination.

This separates the download workload from the final storage location and can be useful when downloading to slower storage such as HDDs.

## Command-Line Arguments Reference

Kemoffu Downloader builds the corresponding `kemono-dl` CLI arguments from the GUI settings and executes the CLI as a separate process.

For the complete list of available options, run:

```bash
python kemono-dl.py --help
```

The following are some of the main options exposed through the GUI:

| Option                                             | Description                                                |
| -------------------------------------------------- | ---------------------------------------------------------- |
| `--cookies <path>`                                 | Specify an authentication cookie file.                     |
| `--inline`                                         | Save images embedded in post content.                      |
| `--content` / `--comments`                         | Save post content as HTML and optionally include comments. |
| `--json`                                           | Save raw post data as JSON.                                |
| `--extract-links` / `--extract-all-links`          | Extract links from post content or users.                  |
| `--icon` / `--banner` / `--fancards`               | Save profile icons, banners, and fan card information.     |
| `--yt-dlp`                                         | Use `yt-dlp` to retrieve embedded videos.                  |
| `--date` / `--datebefore` / `--dateafter`          | Filter posts by publication date.                          |
| `--fp-added`                                       | Use the site's added date instead of the publication date. |
| `--min-filesize` / `--max-filesize`                | Set minimum and maximum file sizes, e.g. `10mb`, `500kb`.  |
| `--only-filetypes` / `--skip-filetypes`            | Allow or exclude specific file extensions.                 |
| `--dirname-pattern`                                | Define the directory naming pattern.                       |
| `--filename-pattern`                               | Define the attachment filename pattern.                    |
| `--retry` / `--ratelimit-sleep` / `--ratelimit-ms` | Configure retries and rate-limit delays.                   |
| `--proxy <url>`                                    | Specify an HTTP or SOCKS proxy.                            |
| `--dupe-check` / `--local-hash`                    | Enable duplicate detection and local hash verification.    |

> **Note**
>
> This is not intended to be an exhaustive CLI reference.
>
> The authoritative list of options is available through:
>
> ```bash
> python kemono-dl.py --help
> ```

## Important Notes & Limitations

### Direct Messages

The `--dms` option currently cannot retrieve DM history because the required DM API is not available due to changes on the target site.

### Cookie Security

Authentication cookies may contain sensitive login information.

Do **not** share `cookies.txt` with other people or accidentally upload it to GitHub or any other public location.

Treat cookie files as confidential credentials.

### WAF / Rate Limiting

Repeated requests may trigger server-side rate limits or security challenges.

If you frequently encounter `403 Forbidden` or `429 Too Many Requests`, consider increasing the request interval and rate-limit wait settings.

## Troubleshooting

### Q. `kemono-dl.py` or Python cannot be found.

When necessary, the GUI will ask you to select the location of:

* `kemono-dl.py`
* `python.exe`

Select the appropriate file and follow the instructions displayed by the application.

### Q. The built-in browser does not open.

Make sure `PyQt6-WebEngine` is installed:

```bash
pip install PyQt6-WebEngine
```

Restart the application after installing the package if necessary.

### Q. I frequently receive `403 Forbidden` or `429 Too Many Requests`.

Try increasing:

* Request interval
* Rate-limit sleep duration
* Retry count

If a WAF/Turnstile warning is displayed, open the verification dialog and complete the challenge manually before retrying.

## License & Disclaimer

Please use this software at your own risk.

Users are responsible for complying with the terms of service of the target websites and all applicable copyright laws and regulations.

The developer assumes no responsibility for data loss, account restrictions, service interruptions, or any other damages resulting from the use of this software.

````
The developer assumes no responsibility for data loss, account restrictions, or any other damages resulting from the use of this software.

External projects used or referenced by this application are subject to their respective licenses and terms of use.
