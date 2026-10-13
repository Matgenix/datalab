const DATE_GRAINS = new Set(["day", "week", "month", "year"]);

function present(value) {
  return value !== undefined && value !== null && value !== "";
}

function identity(value, fallback) {
  return value?.immutable_id ?? value?.user_id ?? value?.group_id ?? fallback;
}

/** Build a descriptor for a single-valued field. */
export function createScalarGroupDescriptor({ id, label, field = id, getValue, compare }) {
  const readValue = getValue || ((item) => item[field]);
  const descriptor = {
    id,
    label,
    getValues(item) {
      const value = readValue(item);
      return present(value) ? [{ key: value, label: String(value), sortValue: value }] : [];
    },
  };
  if (compare) descriptor.compare = compare;
  return descriptor;
}

/** Build the multi-valued creator descriptor used by inventory tables. */
export function createCreatorsGroupDescriptor({ id = "creators", label = "Creators" } = {}) {
  return {
    id,
    label,
    getValues(item) {
      const creators = item.creatorsAndGroups
        ? item.creatorsAndGroups.filter((entry) => entry.type === "creator")
        : item.creators || [];
      return creators
        .filter((creator) => creator && present(creator.display_name))
        .map((creator) => ({
          key: identity(creator, creator.display_name),
          label: creator.display_name,
          sortValue: creator.display_name,
        }));
    },
  };
}

/** Build the multi-valued tag descriptor used by inventory tables. */
export function createTagsGroupDescriptor({ id = "tags", label = "Tags" } = {}) {
  return {
    id,
    label,
    getValues(item) {
      return (item.tags || [])
        .filter((tag) => tag && (present(tag.immutable_id) || present(tag.name)))
        .map((tag) => ({
          key: identity(tag, tag.name),
          label: tag.name || "Unnamed tag",
          sortValue: tag.name || "",
        }));
    },
  };
}

function parseStoredCalendarDay(value) {
  const match = typeof value === "string" ? value.match(/^(\d{4})-(\d{2})-(\d{2})/) : null;
  if (!match) return null;

  const [, yearText, monthText, dayText] = match;
  const year = Number(yearText);
  const month = Number(monthText);
  const day = Number(dayText);
  const date = new Date(Date.UTC(year, month - 1, day));
  if (
    date.getUTCFullYear() !== year ||
    date.getUTCMonth() !== month - 1 ||
    date.getUTCDate() !== day
  ) {
    return null;
  }
  return date;
}

function isoDay(date) {
  return date.toISOString().slice(0, 10);
}

function localisedDate(date, options = {}) {
  return date.toLocaleDateString(undefined, { ...options, timeZone: "UTC" });
}

/** Build a newest-first calendar descriptor without timezone-shifting stored dates. */
export function createDateGroupDescriptor({
  id = "date",
  label = "Date",
  field = "date",
  grain = "month",
} = {}) {
  if (!DATE_GRAINS.has(grain)) throw new Error(`Unsupported date grouping grain: ${grain}`);

  return {
    id,
    label,
    grain,
    getValues(item) {
      const day = parseStoredCalendarDay(item[field]);
      if (!day) return [];

      let key;
      let valueLabel;
      if (grain === "day") {
        key = isoDay(day);
        valueLabel = localisedDate(day);
      } else if (grain === "week") {
        const monday = new Date(day);
        monday.setUTCDate(day.getUTCDate() - ((day.getUTCDay() + 6) % 7));
        key = isoDay(monday);
        valueLabel = `Week of ${localisedDate(monday)}`;
      } else if (grain === "year") {
        key = String(day.getUTCFullYear());
        valueLabel = key;
      } else {
        key = isoDay(day).slice(0, 7);
        valueLabel = localisedDate(day, { month: "long", year: "numeric" });
      }

      return [{ key, label: valueLabel, sortValue: key }];
    },
    compare(a, b) {
      return String(b.sortValue).localeCompare(String(a.sortValue));
    },
  };
}

/** Convert a group-by menu entry into the descriptor consumed by DynamicDataTable. */
export function createGroupDescriptor(field) {
  if (field.id === "creators") return createCreatorsGroupDescriptor(field);
  if (field.id === "tags") return createTagsGroupDescriptor(field);
  if (field.id === "date") return createDateGroupDescriptor(field);
  return createScalarGroupDescriptor(field);
}
