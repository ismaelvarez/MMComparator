import argparse
import json
import sys
import os

SOURCES = []


OUTPUT = ""
OUTPUT_FILE = ""

class BColors:
    HEADER = '\033[95m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    GREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    END_C = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'


TAB = "\t"

WARNING = "{warn}WARNING!{end_c} %s\n" \
    .format(warn=BColors.WARNING, end_c=BColors.END_C)

PROPERTY_EQUALS = "%s -> {}EQUAL{}\n".format(BColors.GREEN, BColors.END_C)

PROPERTY_NOT_EQUALS = "%s -> {red}NOT EQUAL{end_c}\n" \
    .format(red=BColors.FAIL, end_c=BColors.END_C)

DIFFERENCES = "{header}%s{end_c}: \t<{bold}%s{end_c}>\n" \
    .format(header=BColors.HEADER, bold=BColors.BOLD, end_c=BColors.END_C)

MISSING = "{warn}WARNING!{end_c} %s {bold}%s{end_c} {red}IN{end_c} %s but {red}NOT IN{end_c} %s \n" \
    .format(warn=BColors.WARNING, red=BColors.FAIL, end_c=BColors.END_C, bold=BColors.BOLD)

MISSING_CONF = "{warn}WARNING!{end_c} Missing configuration {bold}%s{end_c} in %s\n" \
    .format(warn=BColors.WARNING, end_c=BColors.END_C, bold=BColors.BOLD)

WRONG_ARRAY_CONF = "{warn}WARNING!{end_c} Wrong array configuration\n" \
    .format(warn=BColors.WARNING, end_c=BColors.END_C)

INFO = "{}%s %s{}\n".format(BColors.BOLD, BColors.END_C)

COMPARING_MESSAGE = "-> Comparing {header}%s{end_c} with {header}%s{end_c}" \
    .format(header=BColors.HEADER, end_c=BColors.END_C)

# JSON paths
JAVADOC = "JavaDoc"
DATABASE = "Database"
IR = "IR"
PROFILES = "Profiles"

JAVADOC_JSON = ""
DATABASE_JSON = ""
IR_JSON = ""
PROFILES_JSON = ""

# Verbose
JUST_DIFFERENCES = 0
ALL_TRACES = 1
VERBOSE = JUST_DIFFERENCES

# Monitor Properties

COMMON_PROPERTIES = ["description", "type", "units"]
MONITOR_PROPERTIES = ["upper_limit", "lower_limit", "default_sampling_period", "default_storage_period"]
ARRAY_PROPERTIES = ["width", "height"]
SPECIAL_PROPERTIES = ["values"]


COMPARATOR_RULES = [
    {
        "fields": SPECIAL_PROPERTIES,
        "compare": [IR, JAVADOC]
    }
]

# MONITOR_PROPERTIES = ["upper_limit", "lower_limit", "default_sampling_period", "default_storage_period"]


SOURCE_A_NAME = ""
SOURCE_B_NAME = ""


# Compare1: IR <-> Javadoc
# Compare2: IR <-> Profile
# Compare3: IR <-> Database

# Compare4: Javadoc <-> Profile
# Compare5: Javadoc <-> Database

# Compare6: Profile <-> Database


def compare_strings(string1, string2):
    return string1 == string2


def search(instance, data):
    for config in data:
        if instance.startswith("/"):
            instance = instance[1:]
        if instance == config['instance']:
            return config
    return None


def check_magnitude(magnitude):
    output = ""
    magnitude_ok = True
    keys = magnitude.keys()
    for elem in MONITOR_PROPERTIES:
        if elem not in keys:
            magnitude_ok = False
            output += 3 * TAB + MISSING_CONF % elem

    # Check array configuration
    if "type" in keys and "Array" in magnitude["type"]:
        if not check_array_configuration(magnitude):
            magnitude_ok = False
            output += 4 * TAB + WRONG_ARRAY_CONF

    if not check_array_configuration(magnitude):
        magnitude_ok = False
        output += 4 * TAB + WRONG_ARRAY_CONF

    return magnitude_ok, output


def check_array_configuration(magnitude1):
    if "Array2D" in magnitude1["type"]:
        return all([elem in magnitude1.keys() for elem in ARRAY_PROPERTIES])
    else:
        return "width" in magnitude1.keys()


def compare_magnitude(magnitude1, magnitude2):
    output = ""
    are_mags_equals = True
    properties_checked = []
    source1_name, source2_name = SOURCE_A_NAME, SOURCE_B_NAME
    # Compare mag1 and mag2 and vice-versa
    for _ in range(2):
        for field in magnitude1:
            try:
                if field in properties_checked or not should_compare(field, source1_name, source2_name):
                    continue

                mags_equals = compare_strings(magnitude1[field], magnitude2[field])
                properties_checked.append(field)

                are_mags_equals = are_mags_equals and mags_equals

                if mags_equals and VERBOSE == ALL_TRACES:
                    output += 3 * TAB + PROPERTY_EQUALS % ("Property " + field)

                else:
                    if not mags_equals:
                        output += 3 * TAB + PROPERTY_NOT_EQUALS % ("Property " + field)
                        output += 4 * TAB + DIFFERENCES % (source1_name, magnitude1[field])
                        output += 4 * TAB + DIFFERENCES % (source2_name, magnitude2[field])
            except KeyError:
                are_mags_equals = False
                output += 3 * TAB + MISSING % ("Property", field, source1_name, source2_name)

        # Swap magnitudes values
        magnitude1, magnitude2 = magnitude2, magnitude1
        source1_name, source2_name = source2_name, source1_name

    return are_mags_equals, output


def compare_classname(classname1, classname2):
    output = ""
    class_name_equals = compare_strings(classname1, classname2)
    if VERBOSE == ALL_TRACES:
        output += 2 * TAB + PROPERTY_EQUALS % "Classname"
    else:
        if not class_name_equals:
            output += (2 * TAB + PROPERTY_NOT_EQUALS) % ("Classname", classname1, classname2)

    return class_name_equals, output


def should_compare(monitor, source_name, source_name_to_compare):
    for rule in COMPARATOR_RULES:
        if monitor in rule['fields']:
            sources = [source_name, source_name_to_compare]
            for source in sources:
                if source not in rule['compare']:
                    return False
    return True


def compare_configuration(conf1, conf2):
    output = ""
    conf_equals = True
    monitors_checked = []
    source_name, source_name_to_compare = SOURCE_A_NAME, SOURCE_B_NAME
    for _ in range(2):

        for monitor in conf1['monitors']:
            if monitor in monitors_checked:
                continue
            try:
                if monitor.startswith("/"):
                    output += 2 * TAB + WARNING % "Instance name starts with //"
                    conf_equals = False
                    monitor = monitor[1:]

                mag_equals, mag_output = compare_magnitude(conf1['monitors'][monitor], conf2['monitors'][monitor])
                monitors_checked.append(monitor)
                if not mag_equals or VERBOSE == ALL_TRACES:
                    output += 2 * TAB + INFO % ("Monitor", monitor)

                output += mag_output

                conf_equals = conf_equals and mag_equals
            except KeyError:
                conf_equals = False
                output += 2 * TAB + MISSING % ("Monitor", monitor, source_name, source_name_to_compare)

        conf1, conf2 = conf2, conf1
        source_name, source_name_to_compare = source_name_to_compare, source_name

    return conf_equals, output


def compare_json_files(json1, json2):
    json_equals = True
    output = ""
    magnitudes_checked = []
    source_name, source_name_to_compare = SOURCE_A_NAME, SOURCE_B_NAME
    for _ in range(2):
        for config in json1:
            if config['instance'] in magnitudes_checked:
                continue

            config2 = search(config['instance'], json2)

            if config2 is not None:

                conf_equals, conf_output = compare_configuration(config, config2)

                if not conf_equals or VERBOSE == ALL_TRACES:
                    output += TAB + INFO % ("Instance", config['instance'])
                json_equals = json_equals and conf_equals
                output += conf_output
            else:
                json_equals = False
                output += TAB + MISSING % ("Instance", config['instance'], source_name, source_name_to_compare)

            magnitudes_checked.append(config['instance'])
        json1, json2 = json2, json1
        source_name, source_name_to_compare = source_name_to_compare, source_name
    return json_equals, output


def read_json(path):
    try:
        with open(path, "r") as file:
            return json.load(file)
    except FileNotFoundError:
        print("File %s not found" % path)
        sys.exit()


def save_output():
    global OUTPUT
    for attr, value in BColors.__dict__.items():
        if not attr.startswith("__"):
            OUTPUT = OUTPUT.replace(value, "")
    with open(os.path.join(OUTPUT_FILE, "output"), "w") as file:
        file.write(OUTPUT)


def start():
    global SOURCE_A_NAME
    global SOURCE_B_NAME
    global OUTPUT
    for i in range(len(SOURCES) - 1):
        SOURCE_A_NAME, json1 = SOURCES[i]
        for j in range(i + 1, len(SOURCES)):
            SOURCE_B_NAME, json2 = SOURCES[j]
            output = COMPARING_MESSAGE % (SOURCE_A_NAME, SOURCE_B_NAME)
            OUTPUT += output + "\n"
            print(output)
            json_equals, compare_output = compare_json_files(json1, json2)
            if not json_equals or VERBOSE == ALL_TRACES:
                # compare_output = compare_output.replace("conf1", name).replace("conf2", name_to_compare)
                print(compare_output)
                OUTPUT += compare_output  + "\n"
            else:
                if json_equals:
                    ok = TAB + "{} OK {}".format(BColors.GREEN, BColors.END_C)
                    OUTPUT += ok + "\n"
                    print(ok)
    save_output()


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Sanity check of the configuration of instances and '
                                                 'magnitudes between profiles, .dev files, JavaDocs and Database.'
                                                 'Compare the output files looking for differences ')
    parser.add_argument('-j', '--javadoc', help='<Required> Set the location of JSON file generated by JavaDoc script',
                        default=False)
    parser.add_argument('-db', '--database', help='<Required> Set the location of JSON file generated by Database '
                                                  'script', default=False)
    parser.add_argument('-ir', '--interface', help='<Required> Set the location of JSON file generated by IR script',
                        default=False)
    parser.add_argument('-p', '--profile', help='<Required> Set the location of JSON file generated by profile script',
                        default=False)

    parser.add_argument('-o', '--output', help='<Optional> Set file location for script output')

    parser.add_argument('-v', '--verbose', help='<Optional> Set verbose. 0 for just differences, 1 for all traces',
                        default=0, type=int)

    args = parser.parse_args()

    if args.interface:
        IR_JSON = args.interface
        SOURCES.append(('IR', read_json(IR_JSON)))

    if args.javadoc:
        JAVADOC_JSON = args.javadoc
        SOURCES.append(('JavaDoc', read_json(JAVADOC_JSON)))

    if args.profile:
        PROFILES_JSON = args.profile
        SOURCES.append(('Profiles', read_json(PROFILES_JSON)))

    if args.database:
        DATABASE_JSON = args.database
        SOURCES.append(('Database', read_json(DATABASE_JSON)))

    if args.output:
        OUTPUT_FILE = args.output

    if len(SOURCES) == 0:
        print("Its required to add at least two source JSON files")

    VERBOSE = args.verbose

    if VERBOSE > 1:
        VERBOSE = ALL_TRACES

    start()
