import os
import shutil
import time
import zipfile
import string
from difflib import SequenceMatcher

import mangadex
import requests
import regex as re
from mangadex import Chapter, CoverArt, Manga
from unidecode import unidecode

# Tested On: Python 3.9.12
# Requirements: pip3 install mangadex && pip3 install requests && pip3 install unidecode
# Requires specific mangadex pypi version, until I get around to updating the code.

# Mangadex Volume Downloader/Packer


# volume class
class Volume:
    def __init__(self, volume_number, cover=None):
        self.volume_number = volume_number
        self.chapters = []
        self.cover = cover


# Checks the similarity of two strings
def similar(a, b):
    if a == "" or b == "":
        return 0.0
    else:
        return SequenceMatcher(None, a.lower(), b.lower()).ratio()


# convert each volume to a float
def convert_volume_to_float(chapters):
    for chapter in chapters:
        if isinstance(chapter.volume, str):
            try:
                chapter.volume = float(chapter.volume)
            except ValueError:
                chapter.volume = 0.0
        elif chapter.volume is None:
            chapter.volume = 0.0
    return chapters


# filter all chapter by volume number
def filter_chapters_by_volume_number(chapters, volume_number):
    return [
        chapter
        for chapter in convert_volume_to_float(chapters)
        if chapter.volume == volume_number
    ]


def check_feed_for_missing_chapters_and_volumes(manga_feed, check_type):
    """
    Checks for missing chapters or volumes in a manga feed
    """
    missing = []
    if not manga_feed:
        return missing

    if check_type == "chapters":
        manga_feed.sort(key=lambda chapter: chapter.chapter)
        lowest = int(manga_feed[0].chapter)
        highest = int(manga_feed[-1].chapter)
        attribute_name = "chapter"
    elif check_type == "volumes":
        manga_feed = convert_volume_to_float(manga_feed)
        manga_feed.sort(key=lambda chapter: chapter.volume)
        lowest = int(manga_feed[0].volume)
        highest = int(manga_feed[-1].volume)
        attribute_name = "volume"
    else:
        return missing

    attribute_values = {getattr(chapter, attribute_name) for chapter in manga_feed}
    for value in range(lowest, highest + 1):
        if value not in attribute_values and (
            check_type == "chapters" and value + 0.1 not in attribute_values
        ):
            missing.append(value)

    return missing


def group_chapters_by_volume(manga_feed):
    """
    Groups chapters by volume, and sorts by volume number
    """
    volumes = {}
    for chapter in manga_feed:
        volume_number = chapter.volume
        if volume_number not in volumes:
            volumes[volume_number] = Volume(volume_number)
        volumes[volume_number].chapters.append(chapter)

    sorted_volumes = sorted(volumes.values(), key=lambda volume: volume.volume_number)
    return sorted_volumes


def get_input_from_user(prompt, acceptable_values=None, example=None):
    """
    Gets input from the user, and validates it against the acceptable_values
    """
    if example:
        if isinstance(example, list):
            example_str = " or ".join(f'"{item}"' for item in example)
        else:
            example_str = f'"{example}"'
        prompt = f"{prompt} ({example_str}): "
    else:
        prompt = f"{prompt}: "

    while True:
        user_input = input(f"\n{prompt}")
        if user_input and (not acceptable_values or user_input in acceptable_values):
            return user_input
        print("\tInvalid input")


def filter_series_by_similarity_score(series, compare_title, required_similarity_score):
    """
    Filters the series by using the similar function
    and if the compare_title and title, or compare_title and alt_title are similar enough
    then the series is added to the filtered_series list
    """
    global series_name
    filtered_series = []
    found = False

    print(f"\t\tTotal Series: {len(series)}")

    for manga in series:
        index = series.index(manga) + 1

        if found:
            break

        print(f"\t\t\t[{index}/{len(series)}]  Series: {manga.url}")

        # Combine the title and altTitles into one list
        titles = [manga.title] + manga.altTitles if manga.title else manga.altTitles

        if not titles:
            print("\t\t\tERROR: manga.title is None")
            continue

        print(f"\t\t\t\tTitles:")
        for title in titles:
            if not title:
                print("\t\t\t\t\tERROR: title is None")
                continue

            if title:
                title_key = next(iter(title.keys()))
                title_value = next(iter(title.values()))
                print(f"\t\t\t\t\t{title_key}: {title_value}")

                # remove all punctuation
                title_value = title_value.translate(
                    str.maketrans("", "", string.punctuation)
                ).strip()
                compare_title_clean = compare_title.translate(
                    str.maketrans("", "", string.punctuation)
                ).strip()

                # remove duplicate spaces
                title_value = re.sub(" +", " ", title_value)
                compare_title_clean = re.sub(" +", " ", compare_title_clean)

                similarity_score = similar(title_value, compare_title_clean)
                if similarity_score >= required_similarity_score:
                    print(
                        f"\t\t\t\t\t\tMatch: ({similarity_score} >= {required_similarity_score})"
                    )
                    filtered_series.append(manga)
                    found = True
                    series_name = compare_title
                    break

    return filtered_series


# gets the most frequent group_ids in the chapter list
def get_most_frequent_group_ids(chapters):
    group_ids = {}
    for chapter in chapters:
        if chapter.group_id not in group_ids:
            group_ids[chapter.group_id] = 0
        group_ids[chapter.group_id] += 1

    sorted_group_ids = sorted(
        group_ids.items(), key=lambda group_id: group_id[1], reverse=True
    )
    return sorted_group_ids


def remove_duplicate_chapters(manga_feed):
    """
    Removes duplicate chapters from a manga feed.
    """
    new_manga_feed = []
    chapter_numbers = {}
    for chapter in manga_feed:
        if chapter.chapter in chapter_numbers:
            print(
                f"\t\tDuplicate Chapter Number: {chapter.chapter}\n"
                f"\t\t\tGroup ID (current): {chapter.group_id}\n"
                f"\t\t\tGroup ID (previous): {chapter_numbers[chapter.chapter].group_id}"
            )
            print(f"\t\t\t\tKeeping: {chapter.group_id}\n")
        else:
            new_manga_feed.append(chapter)
            chapter_numbers[chapter.chapter] = chapter
    return new_manga_feed


def filter_covers_and_volumes(covers, volumes):
    """
    Filters a list of manga covers and volumes based on their volume number.
    """
    filtered_covers = []
    filtered_volumes = []

    for cover in covers:
        found = False
        for volume in volumes:
            if volume.volume_number == cover.volume:
                found = True
                break
        if found:
            filtered_covers.append(cover)
        else:
            print(f"\t\tRemoving {cover.volume}, cover not found in volumes")

    for volume in volumes:
        found = False
        for cover in covers:
            if volume.volume_number == cover.volume:
                found = True
                break
        if found:
            filtered_volumes.append(volume)
        else:
            print(f"\t\tRemoving {volume.volume_number}, volume not found in covers")

    return filtered_covers, filtered_volumes


def get_chapter_info(chapter):
    """
    Returns a string with information about a chapter.
    """
    if chapter.title:
        return f"Chapter: {chapter.chapter} - {chapter.title} ({chapter.chapter_id})"
    else:
        return f"Chapter: {chapter.chapter} ({chapter.chapter_id})"


def get_folder_name(series_name, volume_number, source):
    """
    Returns a string with the folder name for a volume.
    """
    volume_number_str = (
        f"{volume_number:02d}" if volume_number < 10 else str(volume_number)
    )
    return f"{series_name} v{volume_number_str} (Scan) ({source})"


# Converts the passed volume_number into a float or an int.
def set_num_as_float_or_int(volume_number):
    try:
        if volume_number != "":
            if isinstance(volume_number, list):
                result = ""
                for num in volume_number:
                    if float(num) == int(num):
                        if num == volume_number[-1]:
                            result += str(int(num))
                        else:
                            result += str(int(num)) + "-"
                    else:
                        if num == volume_number[-1]:
                            result += str(float(num))
                        else:
                            result += str(float(num)) + "-"
                return result
            elif isinstance(volume_number, str) and re.search(r"\.", volume_number):
                volume_number = float(volume_number)
            else:
                if float(volume_number) == int(volume_number):
                    volume_number = int(volume_number)
                else:
                    volume_number = float(volume_number)
    except Exception as e:
        print(
            "Failed to convert volume number to float or int: "
            + str(volume_number)
            + "\nERROR: "
            + str(e),
        )
        return ""
    return volume_number


def format_chapter_and_volume_numbers(chapter_number, volume_number):
    """
    Returns a string with the formatted chapter and volume numbers.
    """

    chapter_number_convert = set_num_as_float_or_int(chapter_number)

    if isinstance(chapter_number_convert, int):
        chapter_str = (
            str(chapter_number_convert).zfill(3)
            if chapter_number_convert < 100
            else str(chapter_number_convert)
        )
    elif isinstance(chapter_number_convert, float):
        chapter_str = (
            str(chapter_number_convert).zfill(5)
            if chapter_number_convert < 100
            else str(chapter_number_convert)
        )

    volume_str = (
        str(volume_number).zfill(2) if volume_number < 10 else f"{volume_number}"
    )
    return f"c{chapter_str} (v{volume_str})"


# Whether or not to ask the user for values
get_user_input = True

# The number of API hits made
number_of_api_hits = 0

# The default search string
DEFAULT_SEARCH = "Gal Assistant"

# The required score when comparing two strings likeness, for it to be considered a match.
requried_similarity_score = 0.9790
series_name = None
source = "MangaDex"

# time to sleep in-between page requests
sleep_time = 5

# the output path for the generated files
output_path = "/Users/zach/mangadex"

volume_number = None
sort = False
limit = 100
offset = None
language = "ja"
only_these_volumes = []


def main():
    global number_of_api_hits

    # Create the output path if it doesn't exist
    if output_path and not os.path.exists(output_path):
        try:
            os.makedirs(output_path)
        except OSError as e:
            print(f"Error creating output path: {e}")
            return

    search = DEFAULT_SEARCH

    # Get the search string from the user
    if get_user_input:
        search = get_input_from_user("Enter manga name", [])

    # Get the manga feed
    api = mangadex.Api()

    # Search for the manga
    manga_series = api.get_manga_list(
        title=search, limit=limit, offset=offset, originalLanguage=[language]
    )

    # Replace : with " - " in the search string
    search = search.replace(":", " - ")

    print(f"\nSearching Mangadex:\n\tSearch: {search}")

    number_of_api_hits += 1

    if not manga_series:
        print("No manga feed found")
        return
    print("\t\tGot manga feed")

    print("\n\tFiltering series by similarity score...")
    manga_series = filter_series_by_similarity_score(
        manga_series, search, requried_similarity_score
    )

    if not manga_series:
        print("\tNo series found")
        return

    manga_series = manga_series[0]

    manga_chapters = []

    # manga_chapters = api.get_manga_volumes_and_chapters(manga_series.manga_id)

    # # get rid of unassigned chapters
    # if "none" in manga_chapters:
    #     manga_chapters.pop("none")

    # # sort by volume value
    # manga_chapters = sorted(manga_chapters.values(), key=lambda x: float(x["volume"]))

    print("\n\tSeries Link: " + manga_series.url)

    print("\n\tSearching for chapters:")

    done = False
    first = True
    while not done:
        if first:
            manga_search = api.chapter_list(
                translatedLanguage=["en"],
                manga=manga_series.manga_id,
                limit=100,
            )
            first = False
        else:
            manga_search = api.chapter_list(
                translatedLanguage=["en"],
                manga=manga_series.manga_id,
                limit=100,
                offset=len(manga_chapters),
            )
        number_of_api_hits += 1
        if not manga_search:
            done = True
        else:
            print("\t\tGot chapter feed with " + str(len(manga_search)) + " chapters")
            manga_chapters.extend(manga_search)
            time.sleep(sleep_time)

    print(f"\tTotal Chapters: {len(manga_chapters)}")

    # Remove duplicate chapters from manga_chapters
    print("\n\tRemoving any duplicate chapters...")
    manga_chapters = remove_duplicate_chapters(manga_chapters)

    print(f"\n\tNew Total Chapters: {len(manga_chapters)}")

    print("\nChecking for missing chapters and volumes...")
    missing_chapters = check_feed_for_missing_chapters_and_volumes(
        manga_chapters, "chapters"
    )
    missing_volumes = check_feed_for_missing_chapters_and_volumes(
        manga_chapters, "volumes"
    )

    if missing_chapters or missing_volumes:
        if missing_chapters:
            print(
                f"\tMissing chapter(s): {', '.join([str(chapter) for chapter in missing_chapters])}"
            )
        else:
            print("\tNo missing chapters")
        if missing_volumes:
            print(f"\tMissing volume(s): {', '.join(missing_volumes)}")
        else:
            print("\tNo missing volumes")
        return

    print("\tNo missing chapters or volumes")
    print("\tGrouping chapters by volume...")

    volumes = group_chapters_by_volume(manga_chapters)

    average_chapters_per_volume = 0

    # Calulate the average number of chapters for all volumes
    if len(volumes) > 1:
        average_chapters_per_volume = sum(
            [len(volume.chapters) for volume in volumes]
        ) / len(volumes)

    # Remove the last volume if it isn't at least 90% of the chapter average, and inform the user
    # To avoid incomplete volumes
    if average_chapters_per_volume:
        if len(volumes) > 1:
            print("\n\tChecking average chapters per volume:")
            print(
                "\t\tAverage chapters per volume: "
                + str(round(average_chapters_per_volume, 2))
            )
            last_volume = volumes[-1]
            print(
                f"\t\t\tVolume {str(last_volume.volume_number)} has {len(last_volume.chapters)} chapters"
            )
            if len(last_volume.chapters) < average_chapters_per_volume * 0.9:
                volumes.pop(-1)
                print(
                    f"\t\t\t\tRemoved volume {last_volume.volume_number} with {len(last_volume.chapters)} chapters"
                )

    print("\n\tTotal Volumes: " + str(len(volumes)))

    # Ask the user what volumes they want to download
    only_these_volumes = get_input_from_user(
        "\tSpecify volumes to download",
        [],
        '"1,2,3" or "1-3" or "all"',
    )
    if only_these_volumes == "all":
        only_these_volumes = []

    # Filter volumes by user input
    if only_these_volumes:
        # EX: [1,2,3]
        if isinstance(only_these_volumes, list):
            volumes = [
                volume
                for volume in volumes
                if volume.volume_number in only_these_volumes
            ]
        # EX: 1 or 1.0
        elif isinstance(only_these_volumes, int) or isinstance(
            only_these_volumes, float
        ):
            volumes = [
                volume
                for volume in volumes
                if volume.volume_number == only_these_volumes
            ]
        elif isinstance(only_these_volumes, str):
            # EX: 1,2,3
            if re.search(r",", only_these_volumes):
                # remove empty spaces
                split_on_comma = [x.strip() for x in only_these_volumes.split(",")]
                volumes = [
                    volume
                    for volume in volumes
                    if volume.volume_number in split_on_comma
                ]
            # EX: 1-3
            elif re.search(r"-", only_these_volumes):
                split_on_dash = only_these_volumes.split("-")

                # get the lowest and highest values
                lowest = int(split_on_dash[0])
                highest = int(split_on_dash[1])

                # fill in the missing values
                split_on_dash = [x for x in range(lowest, highest + 1)]

                volumes = [
                    volume
                    for volume in volumes
                    if volume.volume_number in split_on_dash
                ]
            else:
                volumes = [
                    volume
                    for volume in volumes
                    if volume.volume_number == only_these_volumes
                ]

    if not volumes:
        print("No volumes found after grouping chapters")
        return

    print("\tGot volumes")

    # Get the cover art
    print("\nGetting covers:")
    covers = api.get_coverart_list(
        manga=manga_series.manga_id,
        limit=100,
    )
    # filter out the covers that are not japanese
    covers = [cover for cover in covers if cover.locale == "ja"]

    if not covers:
        print("\tNo covers found")
    print("\tGot covers")

    # convert cover numbers to floats
    print("\tConverting covers to floats...")
    covers = convert_volume_to_float(covers)

    # remove any duplicate values for cover.volume from covers
    # remove the older one based on the cover.createdAt datetime value
    print("\tRemoving duplicate covers...")
    covers = sorted(covers, key=lambda x: x.createdAt, reverse=True)
    new_covers = []
    for cover in covers:
        if cover.volume not in [x.volume for x in new_covers]:
            new_covers.append(cover)
    covers = new_covers

    # sort covers by volume
    covers.sort(key=lambda x: x.volume)

    # remove any covers that don't have a volume
    print("\tFiltering covers and volumes...")
    covers, volumes = filter_covers_and_volumes(covers, volumes)

    number_of_api_hits += 1

    if len(covers) != len(volumes):
        print(
            f"\tERROR: Number of covers ({len(covers)}) does not match number of volumes ({len(volumes)})"
        )
        return

    cover_dict = {cover.volume: cover.cover_id for cover in covers}

    # add the covers to the volumes
    for volume in volumes:
        if volume.volume_number in cover_dict:
            volume.cover = cover_dict[volume.volume_number]
        else:
            print(f"Cover not found for volume {volume.volume_number}")

    print("\n\tVolumes:")
    for volume in volumes:
        print(f"\t\tVolume: {volume.volume_number}")
        print(f"\t\t\tCover: {volume.cover}")

        print("\t\t\tChapters:")
        for chapter in volume.chapters:
            print(f"\t\t\t\t{get_chapter_info(chapter)}")

    print("\nCreating series folder...")
    series_path = os.path.join(output_path, series_name)
    if not os.path.exists(series_path):
        os.mkdir(series_path)
        print("\tCreated series folder")
        print(f"\t\tFolder Path: {series_path}")
    else:
        print("\tSeries folder already exists, using existing folder")

    print("\nCreating volume folders...")
    for volume in volumes:
        converted_volume_number = (
            int(volume.volume_number)
            if volume.volume_number.is_integer()
            else float(volume.volume_number)
        )
        folder_name = get_folder_name(series_name, converted_volume_number, source)
        folder_path = os.path.join(output_path, series_name, folder_name)
        cbz_path = f"{folder_path}.cbz"

        if os.path.isfile(cbz_path):
            print(f"\tSkipping volume: {folder_name}\n\t\talready exists")
            continue

        print(f"\tVolume: {volume.volume_number}")
        print(f"\tCover: {volume.cover}")

        print(f"\n\tCreating volume folder: {folder_name}")
        print(f"\t\tFolder path: {folder_path}")
        if not os.path.exists(folder_path):
            os.mkdir(folder_path)
            if os.path.exists(folder_path):
                print("\t\t\tFolder created")
            else:
                print("\t\t\tFolder not created, skipping volume...")
                continue
        else:
            print("\t\t\tFolder already exists")

            # if not empty, then delete it
            if len(os.listdir(folder_path)) > 0:
                print("\t\t\tDeleting folder along with contents...")
                # remove the folder along with all of its contents
                shutil.rmtree(folder_path)
                if not os.path.exists(folder_path):
                    print("\t\t\tFolder deleted")
                    # create the folder again
                    os.mkdir(folder_path)
                    if os.path.exists(folder_path):
                        print("\t\t\tFolder recreated")
                    else:
                        print("\t\tFolder not recreated")
                        print("\t\t\tSkipping volume...")
                        continue
                else:
                    print("\t\tFolder not deleted")
                    print("\t\tSkipping volume...")
                    continue
            else:
                print("\t\tFolder is empty")
                print("\t\tUsing folder...")

        if os.path.exists(folder_path):
            print("\n\tGetting volume cover link and downloading...")
            image_link = CoverArt.fetch_cover_image(
                api.get_cover(cover_id=volume.cover)
            )
            number_of_api_hits += 2
            cover_path = None
            if image_link:
                print(f"\t\tGetting cover: {image_link}")
                # download the image into the folder using requests
                # use generic User-Agent
                try:
                    r = requests.get(
                        image_link,
                        stream=True,
                        timeout=10,
                        headers={"User-Agent": "Mozilla/5.0"},
                    )
                except Exception as e:
                    print(f"\t\tError downloading cover: {str(e)}")
                    continue
                if r.status_code == 200:
                    print("\t\t\tCover downloaded")

                    # save the image to the folder
                    first_chapter_number = volume.chapters[0].chapter

                    # format the chapter and volume numbers
                    chapter_and_volume_numbers = format_chapter_and_volume_numbers(
                        first_chapter_number,
                        converted_volume_number,
                    )
                    # get the file extension
                    _, image_link_extension = os.path.splitext(image_link)
                    cover_name = f"{series_name} - {chapter_and_volume_numbers} - p000 [Cover] [{source}]{image_link_extension}"
                    cover_path = os.path.join(folder_path, cover_name)
                    with open(cover_path, "wb") as f:
                        r.raw.decode_content = True
                        shutil.copyfileobj(r.raw, f)
                else:
                    print("\t\t\tCover not downloaded")
                    print("\t\t\tSkipping volume...")
                    continue

            if not cover_path or not os.path.isfile(cover_path):
                print("\t\t\tCover not found")
                print("\t\t\tSkipping volume...")
                continue

            # Download the chapters
            print("\n\t\tGetting chapters...")
            count = 1
            failed_on_page = False

            for chapter in volume.chapters:
                if failed_on_page:
                    break

                if chapter.title:
                    print(f"\t\t\tChapter: {chapter.chapter} - {chapter.title}")
                else:
                    print(f"\t\t\tChapter: {chapter.chapter}")

                # Get the chapter
                chapter_url = chapter.url
                number_of_api_hits += 1

                if chapter_url:
                    # if there's a double slash after .org, then replace it with only one slash
                    if re.search(r"\.org//", chapter_url):
                        chapter_url = re.sub(r"\.org//", ".org/", chapter_url)

                    print("\t\t\tChapter URL: " + chapter_url)

                    # Get the chapter pages
                    try:
                        chapter_pages = Chapter.fetch_chapter_images(chapter)
                    except Exception as e:
                        print(f"\t\t\tError getting chapter pages: {str(e)}")
                        # delete the folder
                        shutil.rmtree(folder_path)
                        break

                    number_of_api_hits += 1

                    if chapter_pages:
                        print("\t\t\tPages:")

                        # download each page into the folder
                        # FORAMT: {series_name} - c{chapter_number} (v{volume_number}) - p{page_number} [{source}] [{title}].{extension}
                        # EX: One Piece - c001 (v01) - p001 [MangaDex] [English] [Scanlation].jpg
                        for page in chapter_pages:
                            page_index = chapter_pages.index(page) + 1
                            page_number = count
                            chapter_number = chapter.chapter
                            page_extension = page.split(".")[-1]

                            if page_number < 10:
                                page_number = f"00{page_number}"
                            elif page_number < 100:
                                page_number = f"0{page_number}"
                            else:
                                page_number = page_number

                            chapter_number = format_chapter_and_volume_numbers(
                                chapter_number,
                                converted_volume_number,
                            )

                            page_name = f"{series_name} - {chapter_number} - p{page_number} [{source}]"

                            if chapter.title:
                                clean_title = re.sub(r'"', "", unidecode(chapter.title))
                                # replace : with " - "
                                clean_title = re.sub(r":", " - ", clean_title).strip()
                                # remove /
                                clean_title = re.sub(r"/", " - ", clean_title).strip()
                                # remove any dual space
                                clean_title = re.sub(
                                    r"\s{2,}", " ", clean_title
                                ).strip()
                                page_name += f" [{clean_title}]"

                            page_name += f".{page_extension}"

                            print(
                                f"\t\t\t\tPage [{int(page_index)}/{len(chapter_pages)}] - {page}"
                            )
                            page_path = os.path.join(folder_path, page_name)
                            print(f"\t\t\t\t\tFile: {page_name}")

                            # Download the page
                            try:
                                r = requests.get(
                                    page,
                                    stream=True,
                                    timeout=10,
                                    headers={"User-Agent": "Mozilla/5.0"},
                                )
                            except Exception as e:
                                print("\t\t\t\t\tPage not downloaded" + str(e))
                                failed_on_page = True
                                continue

                            number_of_api_hits += 1
                            time.sleep(sleep_time)

                            if r.status_code == 200:
                                # Save the page to the folder
                                with open(page_path, "wb") as f:
                                    r.raw.decode_content = True
                                    shutil.copyfileobj(r.raw, f)

                                print("\t\t\t\t\tDownloaded")
                                count += 1
                            else:
                                print("\t\t\t\t\tNot downloaded")

            # Verify that all the pages were downloaded
            if len(os.listdir(folder_path)) != count:
                print("\t\t\tNot all pages downloaded")
                print("\t\t\tSkipping volume...")
                continue

            # Package the folder into a CBZ file
            print("\n\t\t\tPacking folder into CBZ...")

            # Create the CBZ file
            with zipfile.ZipFile(
                cbz_path,
                "w",
                compression=zipfile.ZIP_DEFLATED,
            ) as cbz:
                # Add all the files in the folder to the CBZ
                file_list = os.listdir(folder_path)
                file_list = [file for file in file_list if not file.startswith(".")]
                file_list.sort()

                for file in file_list:
                    file_path = os.path.join(folder_path, file)
                    cbz.write(file_path, file)

            if os.path.isfile(cbz_path):
                print("\t\t\t\tCBZ created")

                # Delete the folder
                print("\n\t\t\tDeleting folder...")
                shutil.rmtree(folder_path)

                if not os.path.exists(folder_path):
                    print("\t\t\t\tFolder deleted")
                else:
                    print("\t\t\t\tFolder not deleted")
            else:
                print("\t\t\t\tCBZ not created")
                print("\t\t\tSkipping volume...")
                continue


def do_another_search():
    choice = input("\nDo you want to do another search? (1. Yes / 2. No): ")
    while choice not in ["1", "2"]:
        choice = input("Enter your choice: ")
    return choice == "1"


if __name__ == "__main__":
    while True:
        main()
        if not do_another_search():
            print("Exiting...")
            break
