import titleCase from "./TitleCase";
import underscroreSpaces from "./underscoreSpaces";
import firstLetterUppercase from "./firstLetterUppercase";
import removeVersion from "./removeVersion";
import timeAgo from "./timeAgo";

// Will be accessed as this.$filters("titleCase", "hello world")

const filters = {
    titleCase,
    underscroreSpaces,
    firstLetterUppercase,
    removeVersion,
    timeAgo,
};

export default filters;
