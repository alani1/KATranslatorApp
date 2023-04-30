
defaultVoice = "Louisa"
voices = {
    # Nice low pitch voice, very slow so needs 10% speedFactor
    'Louisa' : {
        'voiceName' : "de-DE-LouisaNeural",
        'voiceGender' : "FEMALE",
        'speedFactor' : 1.2
    },
    # Multilingual Neural voice
    'Jenny' : {
        'voiceName' : "en-US-JennyMultilingualNeural",
        'voiceGender' : "FEMALE",
        'speedFactor' : 1.05
    },

    'Kasper' : {
        'voiceName' : "de-DE-KasperNeural",
        'voiceGender' : "MALE",
        'speedFactor' : 1.1
    },

    'Amala' : {
        'voiceName' : "de-DE-AmalaNeural",
        'voiceGender' : "FEMALE",
        'speedFactor' : 1.0
    },
}

# Course Descriptions used for the YouTube Video Description
# These need to be manually copied from the KA-Website for every course (channelLink & description) and every unit in that course
courseDescriptions = {
    "computer-programming" : {
        'channelLink' : "https://www.youtube.com/playlist?list=PLirbHvoUlBTu-dd0lDLqxV-W7KE2Kn9Ge",
        'description' : "Lerne, wie du Zeichnungen, Animationen und Spiele mit JavaScript & ProcessingJS programmieren kannst. Oder lerne, wie du Webseiten mit HTML & CSS erstellen kannst. Du kannst all deine Programme teilen, erforschen, was andere erstellt haben und gegenseitig voneinander lernen!",
        'programming' : u"Hast du dich schon mal gefragt, was nötig ist, damit Zeichnungen zum Leben erwachen? Nun, wir müssen mit unserem Computer in einer speziellen Sprache sprechen. In dieser Unterrichtseinheit lernen wir, wie wir die Programmiersprache JavaScript und Processing JavaScript verwenden, um unsere eigenen Zeichnungen und Animationen zu erstellen.",
        'html-css' : "Lerne, wie du mit HTML und CSS Webseiten erstellen kannst. HTML ist die Markup Language, mit der du den Inhalt, die Überschriften, Listen, Tabellen, und mehr auf deiner Seite beschreibst. CSS ist die Stylesheet Language, um die Seite zu gestalten und Farbe, Schriftart, Layout und vieles mehr zu definieren.",
        'sql' : "Hast du dich schon mal gefragt, was nötig ist, damit Zeichnungen zum Leben erwachen? Nun, wir müssen mit unserem Computer in einer speziellen Sprache sprechen. In dieser Unterrichtseinheit lernen wir, wie wir die Programmiersprache JavaScript und Processing JavaScript verwenden, um unsere eigenen Zeichnungen und Animationen zu erstellen.",
        'programming-games-visualizations' : "Wenn du die Einführung in JS hinter dir hast, lernst du hier neue Techniken, die dir helfen werden, Programme aus mehreren Szenen, 3D-Graphiken, Button-Menüs und Arcade-Spiele zu kreieren.",
        'programming-natural-simulations' : "Wenn du die Einführung in JS hinter dir hast, lernst du in diesem Kurs, wie man JS, ProcessingJS und mathematische Konzepte kombiniert, um Natur in deinen Programmen zu simulieren. Dieser Kurs leitet sich ab aus 'The Nature of Code', einem Buch von Daniel Shiffman (natureofcode.com), unter CC BY-NC Lizenz genutzt.",
        'html-css-js': 'Wenn du die Einführung in JS und die Einführung in HTML/CSS hinter dir hast, lernst du in diesem Tutorial mit Hilfe von HTML/CSS und der JavaScript DOM API, deine Webseite interaktiv zu machen.',
        'html-js-jquery' : "Lerne, wie man jQuery, die weltweit beliebteste JS-Browserbibliothek, einsetzt, um Webseiten interaktiv zu machen. Erhalte einen Überblick über die jQuery Bibliothek, lerne den Erfinder kennen und benutze jQuery in einer Webseite.",
        'meet-the-computing-professional-unit': "Was kannst du mit Informatik und Programmierkenntnissen anfangen, so bald du sie gelernt hast? Wir haben Menschen aus allen Teilen der Welt und der Industrie eingeladen, sich dir vorzustellen. Finde heraus,  wie vielfältig unser Feld sein kann!",

    },
    "computer-science" : {
        #For now we use the same course also for Computer Science / Informatik
        'channelLink' : "https://www.youtube.com/playlist?list=PLirbHvoUlBTu-dd0lDLqxV-W7KE2Kn9Ge",
        'description' : "Lerne ausgewählte Themen der Informatik wie z.B. Algorithmen (wie wir häufige Probleme in der Informatik lösen und die Effizienz unserer Lösungen messen können), Kryptografie (wie wir geheime Informationen schützen) und Informationstheorie (wie wir Informationen verschlüsseln und komprimieren).",
        #add computer science units
        'algorithms' : "Wir haben haben uns mit den Professoren Tom Cormen und Devin Balkcom vom Dartmouth College zusammengetan um eine Einführung in die Algorithmen-Theorie inklusive Suchalgorithmen, Sortierung, Rekursion und Graphentheorie zu lehren. Lerne durch eine Kombination aus Artikeln, grafischen Darstellungen,  Übungsaufgaben und Programmierchallenges.",
        'cryptography' : "Wir haben haben uns mit den Professoren Tom Cormen und Devin Balkcom vom Dartmouth College zusammengetan um eine Einführung in die Algorithmen-Theorie inklusive Suchalgorithmen, Sortierung, Rekursion und Graphentheorie zu lehren. Lerne durch eine Kombination aus Artikeln, grafischen Darstellungen,  Übungsaufgaben und Programmierchallenges.",
        'informationtheory' : "Wir haben schon immer miteinander kommuniziert. Obwohl wir uns von Signalfeuern zum Alphabet und zur Elektrizität entwickelt haben, viele Probleme bleiben gleich. Erkunde die Geschichte der Kommunikation vom Rauchzeichen bis zum Informationszeitalter"

    },
    "early-math" : {
        'channelLink': "https://www.youtube.com/playlist?list=PLirbHvoUlBTtvQF1g0pCAelbj1z-YdT5a",
        'description': "Mathe beginnt mit dem Zählen. Es ist die wichtigste Fähigkeit, die wir in unseren jungen Jahren erlernen und wird zum Fundament für alle anderen mathematischen Konzepte. Sobald wir zählen können, können wir addieren, subtrahieren, und die Welt um uns herum vermessen. Kurz danach, lernen wir über Stellenwerte, Graphen, Zeit, Geld und Formen."
    }

}