"""
Music recognition data - artists, genres, and keywords.

This file contains all the hardcoded music data extracted from the
monolithic tool selector. Consider moving to YAML/JSON in the future.
"""

# Non-music "play" contexts that should NEVER trigger music
NON_MUSIC_PLAY_PHRASES = [
    'play a game', 'play game', 'play games', 'play video game', 'play the game',
    'play a video', 'play video', 'play this video', 'play the video',
    'play a role', 'play the role', 'play a part', 'play the part',
    'play sports', 'play a sport', 'play basketball', 'play football', 'play soccer',
    'play tennis', 'play golf', 'play baseball', 'play hockey',
    'play cards', 'play poker', 'play chess', 'play checkers',
    'play with', 'play around', "let's play", 'wanna play', 'want to play',
    'play a match', 'play the match', 'play a round',
    'play a trick', 'play tricks', 'play a joke', 'play pranks',
    'role play', 'roleplay', 'word play', 'wordplay', 'fair play',
    'at play', "child's play", 'foul play', 'power play'
]

# PLAY music signals
PLAY_SIGNALS = [
    'play', 'put on', 'start playing', 'queue up', 'listen to', 'throw on',
    'blast', 'spin', 'crank up', 'hit me with'
]

# Music-related nouns
MUSIC_NOUNS = [
    'music', 'song', 'artist', 'album', 'track', 'playlist', 'tune', 'jam',
    'tunes', 'jams', 'beats', 'banger', 'anthem'
]

# Comprehensive genres (60+)
GENRES = [
    # Main genres
    'jazz', 'rock', 'pop', 'classical', 'hip hop', 'hiphop', 'rap', 'country', 'r&b', 'rnb',
    'electronic', 'edm', 'house', 'techno', 'indie', 'alternative', 'alt', 'metal',
    'punk', 'blues', 'soul', 'funk', 'reggae', 'folk', 'ambient', 'lo-fi', 'lofi',
    'latin', 'salsa', 'k-pop', 'kpop', 'j-pop', 'jpop', 'disco', 'gospel', 'opera',
    'soundtrack', 'ost', 'instrumental', 'acoustic', 'chill', 'relaxing', 'upbeat',
    'workout', 'party', 'focus', 'sleep', 'study', 'meditation',
    # Subgenres
    'grunge', 'shoegaze', 'post-rock', 'prog rock', 'progressive', 'psychedelic',
    'death metal', 'black metal', 'thrash', 'hardcore', 'emo', 'screamo',
    'trap', 'drill', 'grime', 'dubstep', 'drum and bass', 'dnb', 'trance',
    'deep house', 'tropical house', 'future bass', 'synthwave', 'retrowave',
    'bossa nova', 'samba', 'flamenco', 'afrobeat', 'afrobeats', 'dancehall',
    'ska', 'dub', 'new wave', 'synth pop', 'synthpop', 'dream pop',
    'neo soul', 'motown', 'doo wop', 'swing', 'big band', 'bebop',
    'bluegrass', 'americana', 'outlaw country', 'honky tonk',
    'gregorian', 'baroque', 'romantic', 'contemporary classical',
    'chillhop', 'vaporwave', 'city pop'
]

# Comprehensive artists (200+) - lowercase for matching
ARTISTS = [
    # Classic Rock / Rock
    'beatles', 'the beatles', 'queen', 'led zeppelin', 'pink floyd', 'rolling stones',
    'the rolling stones', 'ac/dc', 'acdc', 'nirvana', 'foo fighters', 'u2', 'coldplay',
    'radiohead', 'oasis', 'green day', 'linkin park', 'red hot chili peppers', 'rhcp',
    'guns n roses', 'gnr', 'bon jovi', 'aerosmith', 'metallica', 'iron maiden',
    'black sabbath', 'deep purple', 'the who', 'the doors', 'cream', 'jethro tull',
    'rush', 'yes', 'genesis', 'king crimson', 'tool', 'system of a down', 'soad',
    'rage against the machine', 'ratm', 'pearl jam', 'soundgarden', 'alice in chains',
    'stone temple pilots', 'weezer', 'blink 182', 'blink-182', 'sum 41', 'the offspring',
    'muse', 'arctic monkeys', 'the strokes', 'kings of leon', 'imagine dragons',
    'twenty one pilots', 'panic at the disco', 'fall out boy', 'my chemical romance', 'mcr',
    'paramore', 'evanescence', 'three days grace', 'breaking benjamin', 'disturbed',
    'five finger death punch', 'ffdp', 'slipknot', 'korn', 'limp bizkit', 'deftones',

    # Pop
    'taylor swift', 'ed sheeran', 'adele', 'bruno mars', 'ariana grande', 'dua lipa',
    'billie eilish', 'the weeknd', 'harry styles', 'olivia rodrigo', 'doja cat',
    'lady gaga', 'beyonce', 'rihanna', 'katy perry', 'justin bieber', 'shawn mendes',
    'post malone', 'halsey', 'sia', 'charlie puth', 'maroon 5', 'one direction', '1d',
    'bts', 'blackpink', 'twice', 'stray kids', 'seventeen', 'exo', 'nct', 'red velvet',
    'newjeans', 'aespa', 'itzy', 'le sserafim', 'ive',
    'selena gomez', 'miley cyrus', 'demi lovato', 'nick jonas', 'jonas brothers',
    'camila cabello', 'fifth harmony', 'little mix', 'lizzo', 'meghan trainor',
    'lorde', 'troye sivan', 'conan gray', 'gracie abrams', 'sabrina carpenter',
    'tate mcrae', 'dove cameron', 'madison beer', 'ava max', 'bebe rexha',

    # Hip Hop / Rap
    'drake', 'kendrick lamar', 'kanye', 'kanye west', 'jay-z', 'jay z', 'eminem',
    'travis scott', 'j cole', 'j. cole', 'lil nas x', 'megan thee stallion',
    'cardi b', 'nicki minaj', 'tyler the creator', 'asap rocky', 'a$ap rocky',
    'future', '21 savage', 'juice wrld', 'xxxtentacion', 'xxx', 'mac miller',
    'logic', 'chance the rapper', 'childish gambino', 'donald glover',
    'lil uzi vert', 'lil baby', 'dababy', 'rod wave', 'polo g', 'lil durk',
    'young thug', 'gunna', 'lil wayne', '50 cent', 'snoop dogg', 'dr dre',
    'ice cube', 'nas', 'tupac', '2pac', 'biggie', 'notorious big', 'wu-tang',
    'outkast', 'andre 3000', 'missy elliott', 'lauryn hill', 'fugees',
    'a tribe called quest', 'atcq', 'de la soul', 'run dmc', 'beastie boys',
    'kid cudi', 'pharrell', 'pusha t', 'jack harlow', 'central cee', 'ice spice',

    # R&B / Soul
    'frank ocean', 'sza', 'daniel caesar', 'h.e.r.', 'jhene aiko', 'summer walker',
    'usher', 'chris brown', 'alicia keys', 'john legend', 'miguel', 'khalid',
    'the weeknd', 'bryson tiller', 'kehlani', 'ari lennox', 'giveon', 'brent faiyaz',
    'steve lacy', 'blood orange', 'anderson paak', 'silk sonic', 'victoria monet',
    'brandy', 'monica', 'mary j blige', 'erykah badu', 'dangelo', 'maxwell',
    'babyface', 'boyz ii men', 'jodeci', 'new edition', 'tlc', "destiny's child",
    'jagged edge', 'dru hill', '112', 'ginuwine', 'aaliyah', 'ashanti', 'keyshia cole',

    # Electronic / EDM
    'daft punk', 'deadmau5', 'skrillex', 'marshmello', 'calvin harris', 'avicii',
    'kygo', 'zedd', 'martin garrix', 'tiesto', 'david guetta', 'diplo',
    'major lazer', 'the chainsmokers', 'flume', 'odesza', 'porter robinson',
    'madeon', 'illenium', 'seven lions', 'above and beyond', 'armin van buuren',
    'kaskade', 'steve aoki', 'hardwell', 'afrojack', 'nicky romero',
    'excision', 'subtronics', 'rezz', 'griz', 'big wild', 'rufus du sol',
    'disclosure', 'kaytranada', 'four tet', 'jamie xx', 'bonobo', 'tycho',
    'boards of canada', 'aphex twin', 'burial', 'flying lotus', 'amon tobin',

    # Country
    'luke combs', 'morgan wallen', 'chris stapleton', 'luke bryan', 'blake shelton',
    'carrie underwood', 'dolly parton', 'johnny cash', 'willie nelson', 'waylon jennings',
    'garth brooks', 'george strait', 'alan jackson', 'kenny chesney', 'tim mcgraw',
    'faith hill', 'shania twain', 'reba mcentire', 'miranda lambert', 'kacey musgraves',
    'maren morris', 'kelsea ballerini', 'carly pearce', 'lainey wilson', 'zach bryan',
    'tyler childers', 'sturgill simpson', 'jason isbell', 'colter wall', 'charley crockett',

    # Jazz / Blues
    'miles davis', 'john coltrane', 'louis armstrong', 'ella fitzgerald',
    'duke ellington', 'charlie parker', 'thelonious monk', 'dizzy gillespie',
    'billie holiday', 'nina simone', 'nat king cole', 'sarah vaughan',
    'chet baker', 'dave brubeck', 'herbie hancock', 'chick corea', 'pat metheny',
    'bb king', 'b.b. king', 'muddy waters', 'howlin wolf', 'john lee hooker',
    'robert johnson', 'stevie ray vaughan', 'srv', 'eric clapton', 'buddy guy',
    'joe bonamassa', 'gary clark jr', 'john mayer', 'kamasi washington',

    # Classical
    'beethoven', 'mozart', 'bach', 'chopin', 'vivaldi', 'tchaikovsky',
    'brahms', 'schubert', 'handel', 'haydn', 'liszt', 'mendelssohn',
    'debussy', 'ravel', 'stravinsky', 'rachmaninoff', 'mahler', 'wagner',
    'dvorak', 'sibelius', 'grieg', 'verdi', 'puccini', 'rossini',
    'yo-yo ma', 'itzhak perlman', 'lang lang', 'martha argerich', 'andras schiff',

    # Legends / Legacy
    'michael jackson', 'mj', 'prince', 'whitney houston', 'elton john', 'david bowie',
    'madonna', 'stevie wonder', 'fleetwood mac', 'abba', 'eagles', 'dire straits',
    'bob marley', 'bob dylan', 'jimi hendrix', 'eric clapton', 'santana',
    'james brown', 'aretha franklin', 'ray charles', 'marvin gaye', 'otis redding',
    'sam cooke', 'al green', 'barry white', 'diana ross', 'supremes', 'temptations',
    'four tops', 'smokey robinson', 'ike turner', 'tina turner', 'chuck berry',
    'little richard', 'fats domino', 'buddy holly', 'elvis', 'elvis presley',
    'frank sinatra', 'dean martin', 'sammy davis jr', 'tony bennett', 'bing crosby',
    'bee gees', 'earth wind fire', 'earth wind and fire', 'ewf', 'kool and the gang',
    'commodores', 'lionel richie', 'phil collins', 'peter gabriel', 'sting', 'police',
    'talking heads', 'blondie', 'duran duran', 'depeche mode', 'new order', 'the cure',
    'joy division', 'the smiths', 'morrissey', 'r.e.m.', 'rem', 'pixies', 'sonic youth',

    # Modern Indie / Alternative
    'tame impala', 'mgmt', 'vampire weekend', 'bon iver', 'fleet foxes', 'iron and wine',
    'the national', 'interpol', 'modest mouse', 'death cab for cutie', 'the shins',
    'the decemberists', 'arcade fire', 'lcd soundsystem', 'st vincent', 'phoebe bridgers',
    'japanese breakfast', 'snail mail', 'soccer mommy', 'boygenius', 'big thief',
    'beach house', 'grizzly bear', 'animal collective', 'of montreal', 'neutral milk hotel',
    'sufjan stevens', 'andrew bird', 'father john misty', 'the war on drugs', 'kurt vile',
    'mac demarco', 'rex orange county', 'boy pablo', 'cavetown', 'girl in red',
    'clairo', 'beabadoobee', 'wallows', 'dayglow', 'still woozy', 'dominic fike',

    # Latin
    'bad bunny', 'j balvin', 'daddy yankee', 'ozuna', 'maluma', 'anuel aa',
    'rauw alejandro', 'karol g', 'becky g', 'nicky jam', 'farruko', 'sech',
    'shakira', 'jennifer lopez', 'jlo', 'enrique iglesias', 'ricky martin',
    'luis fonsi', 'marc anthony', 'romeo santos', 'prince royce', 'juan luis guerra',
    'carlos vives', 'juanes', 'mana', 'soda stereo', 'cafe tacvba',
    'rosalia', 'c tangana', 'arca', 'peso pluma', 'fuerza regida', 'grupo frontera'
]

# Control signals for music playback
CONTROL_SIGNALS = [
    'pause', 'stop', 'resume', 'skip', 'next', 'previous', 'back',
    'volume up', 'volume down', 'mute', 'louder', 'quieter', 'softer',
    'turn it up', 'turn it down', 'next song', 'previous song',
    'skip this', 'play next', 'go back'
]

# Visualizer signals
VISUALIZER_SIGNALS = [
    'light show', 'music visualizer', 'visualizer', 'dance with music',
    'sync lights', 'lights dance', 'party lights', 'make lights dance',
    'lights to the music', 'disco mode', 'rave mode', 'club lights'
]

# Information request indicators (not playback)
INFO_REQUEST_WORDS = [
    'about', 'information', 'who is', 'what is', 'search for',
    'tell me about', 'wiki', 'wikipedia'
]

# Non-music play contexts
NON_MUSIC_CONTEXT_WORDS = [
    'game', 'video', 'role', 'part', 'character', 'sport', 'match', 'quiz'
]
