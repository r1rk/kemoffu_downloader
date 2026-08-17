# Kemoffu Downloader

A multithreaded downloader that provides a GUI for operating the `kemono-dl` CLI.

It allows you to process large numbers of URLs at once, customize what content and file types to download, filter posts by date or file size, and flexibly control output paths and file naming.

The actual download process is handled by the `kemono-dl` CLI engine, while Kemoffu adds its own features such as task management, in-memory search, responsive image search, WAF/Turnstile handling, two-stage staging storage, download history, and file preview.

> **Note**
>
> This application provides a large number of configuration options.
>
> You can hover over GUI controls to display tooltips with detailed explanations.
>
> This README focuses on the main features and GUI-specific functionality.

## Features

### 🚀 Download & Task Management

- **Batch URL processing**  
  Specify multiple URLs, one per line. URLs can also be added via drag and drop.
- **Parallel task processing**  
  Multiple download tasks can be processed concurrently.
- **Favorites batch processing**  
  Process favorite users and posts from Kemono / Coomer / Pawchive in bulk.
- **Real-time progress display**  
  View task progress, transfer speed, ETA, and other information directly in the GUI.
- **Suspend & Resume**  
  Pause, resume, or stop download processes and individual tasks.
- **Batch transfer (Staging)**  
  When using a custom output directory, downloaded files are first stored in a temporary working area and moved to the specified destination after processing is complete.

### 📦 Customizable Download Targets

The GUI exposes various `kemono-dl` options, allowing you to control exactly what data is saved.

- **Attachments**  
  Download images, videos, archives, and other attached files.
- **Post content (HTML)**  
  Save post content as HTML.
- **Comments**  
  Include post comments in the saved HTML.
- **Inline images**  
  Save images embedded in post content.
- **Metadata (JSON)**  
  Save post data as JSON.
- **Link extraction**  
  Extract links from post content or generate link lists on a per-user basis.
- **User information**  
  Download profile icons, banners, fan cards, announcements, and other user information.
- **External tools**  
  Use `yt-dlp` to download embedded videos.

### 🧰 Filters & File Organization

- **Date filters**  
  Filter posts by publication date or the date they were added to the site.
- **User update date filters**  
  Filter based on the date the creator information was updated.
- **File size limits**  
  Specify minimum and maximum file sizes.
- **File extension filters**  
  Specify which file types to include or exclude.
- **Keyword filters**  
  Filter posts by keywords contained in post titles or file names.
- **Directory & filename patterns**  
  Customize directory and file names using variables such as `{service}`, `{username}`, and `{user_id}`.

### ⚙️ Network & Automatic Handling

- **Automatic retry handling**  
  Wait and retry automatically after download failures or rate limiting.
- **Proxy support**  
  Supports HTTP and SOCKS-based proxies.
- **Proxy management**  
  Provides status and error handling when using multiple proxies.
- **Duplicate prevention**  
  Prevent duplicate downloads using local file checks and hash comparisons.
- **Interrupted download recovery**  
  Resume interrupted downloads using `.part` files.
- **Automatic retry for unlisted users**  
  Users that cannot be found through the creator list can be retried using the direct user API.

## ✨ GUI-Specific Features

### 🌐 WAF / Turnstile Handling

When information requests are blocked by site-side WAF / Turnstile protection, the GUI can open the built-in browser and allow you to complete the verification manually.

1. A confirmation dialog is displayed when WAF / Turnstile protection is detected.
2. Open the target site in the built-in browser.
3. Complete the displayed challenge manually.
4. Click **"Get Session and Retry"**.
5. The obtained session is used to retry the affected information request.

This feature requires `PyQt6-WebEngine`.

> **Note**
>
> This feature is intended to handle WAF-related access restrictions for information requests. It does not require browser verification for every normal download.

### 🎨 Responsive Image Search (Visual Search)

A creator image search feature available from the Search tab.

- Automatically arranges search cards according to the window width
- Search by creator name or ID
- Switch between Kemono / Coomer / Pawchive search targets
- Retry failed image requests individually
- Provides a **"Next Page"** card at the end of search results
- Add URLs directly from search results to the download list

The number of image retrieval retries can also be configured from the GUI.

### 🔎 In-Memory Creator Search

Creator information can be stored in a local cache and searched by name or ID.

You can switch between supported services and manually update the cache when necessary.

Search results also display information such as per-service retrieval status and result counts.

### 🗂️ Download History

Download history can be viewed directly from the GUI.

The History tab provides options to:

- Refresh the history
- Open `archive.txt` directly

### 🖼️ Saved File Preview

Completed tasks can be used to locate downloaded files and inspect the saved contents from the GUI.

### 💾 Two-Stage Staging Storage

When a custom output directory is used, the download process and final file storage are separated.

1. Download files to a temporary working directory.
2. Wait until all download processing is complete.
3. Move the files to the specified destination while preserving the directory structure.

The temporary working directory is named `_temp_staging_batch`.

### 🔄 Kemono / Pawchive Favorites Migration

The built-in browser can be used to retrieve favorite information from one site and import it into the other.

This feature requires `PyQt6-WebEngine`.

---

## Requirements & Installation

### 1. Using the packaged `.exe`

Download a pre-built package from the project's releases and run the application.

Python does not need to be installed separately when using the packaged version.

### 2. Running as a Python script

Install Python and the required dependencies:

```bash
pip install PyQt6 psutil
````

To use the built-in browser, install the following additional package:

```bash
pip install PyQt6-WebEngine
```

Features that require `PyQt6-WebEngine` include:

* WAF / Turnstile verification
* Cookie and login-related browser functions
* Favorites migration
* Other built-in browser functionality

---

## Basic Usage

### 1. Enter URLs

Enter the target URLs in the URL input field.

When specifying multiple URLs, enter one URL per line.

URLs can also be added from search results and other GUI functions.

When a creator page URL is specified, the application can retrieve creator information through the API, expand the available posts, and create download tasks from them.

### 2. Adjust the settings

Switch between the available tabs and configure the options you need.

Common settings include:

* Download targets
* Date, file size, and file extension filters
* Directory and filename patterns
* Cookies
* Proxies
* Retry settings
* Rate-limit settings
* Parallel process count

Hovering over a GUI option displays a tooltip containing additional information.

### 3. Select the output directory

You can use the default output directory or specify a custom destination.

When a custom destination is enabled, downloaded files are moved from the staging area to the specified destination after the download process is complete.

### 4. Start the download

Click **"▶ Start Download"** to begin processing.

Task progress, transfer speed, and logs are displayed in real time.

---

## Advanced Features

### WAF / Turnstile

When access to an information API is blocked by WAF / Turnstile protection, the built-in browser can be used to complete the verification manually.

After verification is completed, the obtained session can be used to retry the affected information request.

If the built-in browser cannot be opened, make sure that `PyQt6-WebEngine` is installed.

### Visual Search

Launch it using **"Start Image Search Mode"** in the Search tab.

Search results are arranged as cards according to the current window size, and URLs can be added directly to the download list from the search results.

If an icon or banner fails to load, it is retried individually up to the configured retry count.

### Staging Storage

When a custom output directory is enabled, downloaded files are temporarily stored in:

```text
_temp_staging_batch
```

After all download tasks are complete, the files are moved to the specified destination while preserving the directory structure.

---

## CLI Options

The GUI dynamically builds `kemono-dl` CLI arguments based on the selected settings.

The following are the main CLI options available through the GUI.

| Option                               | Description                                                                       |
| ------------------------------------ | --------------------------------------------------------------------------------- |
| `--cookies <FILE>`                   | Specify a cookie file                                                             |
| `--inline`                           | Save inline images contained in post content                                      |
| `--content`                          | Save post content as HTML                                                         |
| `--comments`                         | Save post comments as HTML                                                        |
| `--json`                             | Save post data as JSON                                                            |
| `--extract-links`                    | Extract links from post content                                                   |
| `--extract-all-links`                | Extract links on a per-user basis                                                 |
| `--icon`                             | Save the user's profile icon                                                      |
| `--banner`                           | Save the user's profile banner                                                    |
| `--fancards`                         | Save fan cards                                                                    |
| `--announcements`                    | Save user announcements                                                           |
| `--yt-dlp`                           | Use `yt-dlp` to download embedded videos                                          |
| `--date YYYYMMDD`                    | Download posts from the specified date onward                                     |
| `--datebefore YYYYMMDD`              | Download posts before the specified date                                          |
| `--dateafter YYYYMMDD`               | Download posts after the specified date                                           |
| `--fp-added`                         | Use the site's post-added date instead of the publication date for date filtering |
| `--user-updated-datebefore YYYYMMDD` | Filter by user update date                                                        |
| `--user-updated-dateafter YYYYMMDD`  | Filter by user update date                                                        |
| `--min-filesize SIZE`                | Specify the minimum file size                                                     |
| `--max-filesize SIZE`                | Specify the maximum file size                                                     |
| `--only-filetypes EXT`               | Download only the specified file types                                            |
| `--skip-filetypes EXT`               | Exclude the specified file types                                                  |
| `--only-postname WORDS`              | Download only posts whose titles contain the specified text                       |
| `--skip-postname WORDS`              | Exclude posts whose titles contain the specified text                             |
| `--only-filename WORDS`              | Download only files whose names contain the specified text                        |
| `--skip-filename WORDS`              | Exclude files whose names contain the specified text                              |
| `--dirname-pattern PATTERN`          | Specify the directory naming pattern                                              |
| `--filename-pattern PATTERN`         | Specify the attachment filename pattern                                           |
| `--retry COUNT`                      | Number of retries after download failures                                         |
| `--ratelimit-sleep SEC`              | Wait time after rate limiting                                                     |
| `--ratelimit-ms MS`                  | Specify the request interval                                                      |
| `--proxy PROXY`                      | Specify a proxy                                                                   |
| `--local-hash`                       | Check the hashes of existing local files                                          |
| `--dupe-check`                       | Check for duplicate files using hashes and related data                           |
| `--archive FILE`                     | Download only posts that are not recorded in the archive                          |
| `--force-unlisted`                   | Retrieve users directly without relying on the creator list                       |
| `--retry-403 COUNT`                  | Number of retries after HTTP 403 responses                                        |
| `--archives-password`                | Search for archive passwords                                                      |
| `--cache-creators`                   | Cache the creator list                                                            |
| `--cache-creators-expire SEC`        | Specify the creator cache expiration time                                         |

For the complete list of available options, run:

```bash
python kemono-dl.py --help
```

---

## Important Notes & Limitations

### Direct Messages (`--dms`)

Depending on the current API provided by the target site, DM access may not be available.

If the site's DM API is unavailable, specifying `--dms` will not allow DM history to be downloaded.

### Cookie Information

Cookie files may contain authentication information.

Do not share cookie files with other people or accidentally upload them to public repositories such as GitHub.

### Target Sites

Changes to the target site's specifications, APIs, or access restrictions may cause some features of this application to stop working or behave differently.

---

## Troubleshooting

### `kemono-dl.py` cannot be found

When the GUI starts or when the first download is started, you can specify the location of `kemono-dl.py`.

When selecting `kemono-dl.py`, make sure the required `src` directory is also present in the expected location.

The selected path is saved as part of the GUI configuration and can be reused on subsequent launches.

### Python cannot be found

Python is required when running the `kemono-dl.py` script.

Specify the location of `python.exe` from the GUI.

### The built-in browser does not open

Install the following package:

```bash
pip install PyQt6-WebEngine
```

When using the packaged `.exe`, make sure the QtWebEngine components are included correctly in the distribution package.

### Frequent 403 Forbidden / 429 Too Many Requests errors

Try the following:

* Increase the **Request Interval** in the Advanced settings.
* Increase the **Rate Limit Sleep** duration.
* Adjust the retry count if necessary.
* If the WAF / Turnstile confirmation dialog appears, complete the verification using the built-in browser.
* Configure a proxy if necessary.

---

## Data & Configuration Files

GUI settings, history, and other application data are stored in the user's application data directory.

The main files and directories include:

| File / Directory      | Purpose                                              |
| --------------------- | ---------------------------------------------------- |
| `config.json`         | GUI configuration                                    |
| `cookies.txt`         | Cookie information                                   |
| `creators_cache.json` | Creator search cache                                 |
| `archive.txt`         | Download history                                     |
| `_temp_staging_batch` | Temporary working directory used for Staging storage |

Some of these files, especially cookie-related files, may contain sensitive information. Handle them accordingly.

---

## Credits / References

This project was developed with reference to the following projects and tools.

### kemono-dl

`kemono-dl` by L4cache, based on the fork originally created by AlphaSlayer1964.

The actual download engine used by Kemoffu is based on the `kemono-dl` CLI.

### Kemono → Pawchive Favorites Migration Tool

The user script **"Kemono → Pawchive お引っ越しツール（フォロー＆ブックマーク）"** by Misery.

This was referenced when implementing the Kemono / Pawchive favorites migration functionality.

### KemonoDownloader

**"KemonoDownloader"** by VoXDroid.

---

## License & Disclaimer

Use this software at your own risk.

Please comply with the terms of service of the target websites, copyright law, and all other applicable laws and regulations.

The developer assumes no responsibility for data loss, account restrictions, or any other damages resulting from the use of this software.

External projects used or referenced by this application are subject to their respective licenses and terms of use.