"""الترجمة الإنجليزية لبنك الأسئلة: سطر لكل سؤال بنفس ترتيب القائمة العربية (Q ثم Q2).
الصيغة:  السؤال|الجواب الصحيح|خطأ1|خطأ2|خطأ3   (بنفس ترتيب الخيارات العربية)
سكربت البناء يتحقق آليًا من تطابق الأرقام والأسماء اللاتينية بين النسختين."""

E_RAW = r"""
Who is the hero of Naruto?|Naruto Uzumaki|Sasuke Uchiha|Kakashi Hatake|Rock Lee
In Dragon Ball, what do the heroes gather to make a wish?|The Dragon Balls|The Infinity Stones|The Seven Gems|Magic cards
What is the name of the most famous yellow Pokémon?|Pikachu|Charmander|Squirtle|Mew
What is Luffy's dream in One Piece?|To become the Pirate King|To become Hokage|To become a Marine admiral|To become the strongest samurai
Which anime is about a notebook that kills whoever's name is written in it?|Death Note|Bleach|Naruto|Tokyo Ghoul
What is Doraemon?|A robot cat from the future|A ghost dog|A magic bear|A nine-tailed fox
What are the giant man-eating creatures called in Attack on Titan?|Titans|Demons|Ghouls|Angels
What is manga?|Japanese comics|Live-action Japanese films|Japanese food|Traditional Japanese clothing
What is the famous hat Luffy wears?|A straw hat|A samurai hat|A sailor hat|A wizard hat
Which country produces most of the world's anime?|Japan|South Korea|China|The United States
Who is the hero of Detective Conan?|Conan Edogawa (Shinichi Kudo)|Light Yagami|Eren Yeager|Edward Elric
Which sport does the hero of Captain Tsubasa play?|Football (soccer)|Basketball|Tennis|Baseball
Which village does Naruto belong to?|Konoha (Hidden Leaf)|Sunagakure (Hidden Sand)|Kirigakure (Hidden Mist)|Kumogakure (Hidden Cloud)
Which beast is sealed inside Naruto?|The Nine-Tailed Fox|The Black Dragon|The giant serpent|The two-sword tiger
Who is the hero of Death Note?|Light Yagami|L|Ryuk|Mello
Who is the hero of Attack on Titan?|Eren Yeager|Levi Ackerman|Zeke Yeager|Reiner Braun
In Dragon Ball, who is the Prince of all Saiyans?|Vegeta|Gohan|Trunks|Piccolo
Who is the hero of the Pokémon anime?|Ash Ketchum|Gary|Brock|James
Who is the hero of Demon Slayer?|Tanjiro Kamado|Zenitsu Agatsuma|Inosuke Hashibira|Giyu Tomioka
Who is the hero of My Hero Academia?|Izuku Midoriya|Katsuki Bakugo|Shoto Todoroki|Uraraka
Which hero defeats enemies with a single punch in One Punch Man?|Saitama|Genos|Tatsumaki|Bang
What does the Japanese word "kawaii" mean?|Cute|Scary|Strong|Fast
How many Dragon Balls are there in Dragon Ball?|Seven|Five|Nine|Twelve
Which studio produced My Neighbor Totoro and Spirited Away?|Studio Ghibli|MAPPA|Toei Animation|Bones
Who is the hero of Fullmetal Alchemist?|Edward Elric|Roy Mustang|Light Yagami|Izuku Midoriya
In Death Note, who is the genius detective chasing Kira?|L|Mello|Near|Watari
Who is the teacher of Naruto's team (Team 7)?|Kakashi Hatake|Jiraiya|Iruka|Asuma
Who is Eren's childhood friend who always protects him?|Mikasa Ackerman|Historia Reiss|Sasha Braus|Pieck Finger
What is the name of Tanjiro's sister who became a demon?|Nezuko|Shinobu|Kanao|Mitsuri
Who is the hero of Sword Art Online?|Kirito|Asuna|Klein|Leafa
Which swordsman of Luffy's crew fights with three swords?|Zoro|Sanji|Usopp|Franky
Who gave Luffy his straw hat?|Shanks|Ace|Garp|Gol D. Roger
What is the name of Sasuke's older brother?|Itachi|Madara|Obito|Shisui
What is the name of Goku's eldest son?|Gohan|Goten|Trunks|Bardock
What is the name of the cook of the Straw Hat crew?|Sanji|Zoro|Usopp|Jinbe
What is the name of the heroine of Spirited Away?|Chihiro|Satsuki|Kiki|San
What is the original Japanese name of the "Captain Majed" anime?|Captain Tsubasa|Captain Hikaru|Captain Ryo|Captain Gaku
What is Ryuk the death god's favorite fruit?|Apples|Bananas|Oranges|Grapes
What does "cosplay" mean?|Dressing up as characters|Drawing manga|Translating anime|Collecting figures
Who is a "mangaka"?|A manga artist/author|A voice actor|A film director|A translator
Which song is the famous Dragon Ball Z opening?|Cha-La Head-Cha-La|We Are!|Tank!|Gurenge
Who is the hero of Tokyo Ghoul?|Ken Kaneki|Touka Kirishima|Rize|Hide Nagachika
What is the basic principle of alchemy in Fullmetal Alchemist?|Equivalent Exchange|Willpower|Dark energy|The law of blood
Who wrote the One Piece manga?|Eiichiro Oda|Masashi Kishimoto|Akira Toriyama|Tite Kubo
Who wrote Dragon Ball?|Akira Toriyama|Eiichiro Oda|Masashi Kishimoto|Hajime Isayama
Which villain destroyed the Saiyan planet in Dragon Ball?|Frieza|Cell|Majin Buu|Broly
How many Pokémon are in the first generation?|151|100|251|493
What is the special eye of the Uchiha clan called?|Sharingan|Byakugan|Rinnegan|Tenseigan
Which toad sage trained Naruto?|Jiraiya|Orochimaru|Hiruzen Sarutobi|Kakashi
What is Light's family name in Death Note?|Yagami|Amane|Hoshino|Kira
What is the name of Eren's blond, strategic friend?|Armin Arlert|Connie Springer|Jean Kirstein|Reiner Braun
Who is the strongest teacher with a blindfold in Jujutsu Kaisen?|Satoru Gojo|Nanami|Megumi|Geto
Who is the hero of Haikyuu!!?|Shoyo Hinata|Tobio Kageyama|Ryunosuke Tanaka|Kei Tsukishima
In which magazine was One Piece published?|Weekly Shonen Jump|Weekly Shonen Magazine|Weekly Shonen Sunday|Young Animal
What does the "isekai" genre mean?|Heroes transported to another world|School horror stories|Sports stories|School romance
Who are "shojo" manga usually aimed at?|Girls|Children|Adult men|Elderly people
What does "filler" mean in anime?|Episodes that don't follow the original manga|The opening episode|The opening song|A new season
What is the first opening song of the One Piece anime?|We Are!|Cha-La Head-Cha-La|Silhouette|Gurenge
Who is Naruto's father?|Minato Namikaze|Jiraiya|Hiruzen Sarutobi|Fugaku Uchiha
Which studio produced Demon Slayer?|Ufotable|MAPPA|Bones|Wit Studio
Which studio produces the One Piece anime?|Toei Animation|Madhouse|Sunrise|Pierrot
Who is nicknamed the "God of Manga"?|Osamu Tezuka|Hayao Miyazaki|Akira Toriyama|Leiji Matsumoto
What are the mysterious enemies in Neon Genesis Evangelion called?|Angels|Demons|Titans|Ghouls
What is the eye technique of the Hyuga clan in Naruto?|Byakugan|Sharingan|Rinnegan|Sekigan
Which Devil Fruit did Luffy eat at the start?|Gomu Gomu (rubber)|Mera Mera (fire)|Hana Hana|Magu Magu (magma)
What is the name of the Straw Hat crew's first ship?|Going Merry|Thousand Sunny|Red Force|Moby Dick
Who is the "Second Kira" in Death Note?|Misa Amane|Sayu Yagami|Kiyomi Takada|Rem
What power system do hunters use in Hunter x Hunter?|Nen|Chakra|Ki|Haki
Who is Gon's close white-haired friend?|Killua Zoldyck|Kurapika|Leorio|Hisoka
What does "tsundere" mean?|Cold or hostile outside but sweet inside|Always happy|Very shy|Evil
Who are "seinen" manga usually aimed at?|Adult men|Children|Teenage girls|Adult women
What does "seiyuu" mean?|Voice actor|Director|Screenwriter|Character designer
Which studio produced Cyberpunk: Edgerunners?|Studio Trigger|MAPPA|Bones|Ufotable
Which studio produced Chainsaw Man?|MAPPA|Wit Studio|Bones|Ufotable
What is Roy Mustang's alias in Fullmetal Alchemist?|The Flame Alchemist|The Fullmetal Alchemist|The Wind Alchemist|The Iron Alchemist
Who is the genius hero of Dr. Stone?|Senku Ishigami|Taiju Oki|Gen Asagiri|Kohaku
What kind of being is Frieren in Frieren: Beyond Journey's End?|An elf mage|A human swordswoman|A demon|A robot
What is the famous opening of Evangelion called?|A Cruel Angel's Thesis|Tank!|Gurenge|Unravel
Who sang "Gurenge", the Demon Slayer opening?|LiSA|Aimer|Eir Aoi|Aimyon
Who are L's two successors in Death Note?|Mello and Near|Matsuda and Aizawa|Rem and Ryuk|Watari and Roger
Which of these is the name of one of the three walls in Attack on Titan?|Wall Sina|Wall Mira|Wall Tera|Wall Nira
Which studio produced Death Note?|Madhouse|Bones|MAPPA|Wit Studio
Which studio produced Fullmetal Alchemist: Brotherhood?|Bones|Madhouse|Sunrise|Gainax
Which studio produced season 1 of Attack on Titan?|Wit Studio|MAPPA|Bones|Ufotable
Which studio produced Violet Evergarden?|Kyoto Animation|Ufotable|Trigger|Shaft
Which studio produced Naruto and Bleach?|Studio Pierrot|Toei Animation|Madhouse|Bones
Which studio produced Jujutsu Kaisen?|MAPPA|Ufotable|Madhouse|Trigger
Which studio produced Frieren: Beyond Journey's End?|Madhouse|MAPPA|Ufotable|Bones
Who is the author of Berserk?|Kentaro Miura|Naoki Urasawa|Hiromu Arakawa|Takehiko Inoue
In what year did the Pokémon anime start?|1997|1990|2000|1995
In what year did Attack on Titan start airing?|2013|2010|2015|2017
What is the organization where Shinji and most pilots work in Evangelion?|NERV|Akatsuki|SHIELD|Gotei 13
Who pilots Unit 00 in Evangelion?|Rei Ayanami|Asuka Langley|Misato Katsuragi|Ritsuko Akagi
What is Subaru's ability in Re:Zero?|Return by Death|Time stop|Mind reading|Turning into a monster
Who is the hero of Slam Dunk?|Hanamichi Sakuragi|Kaede Rukawa|Takenori Akagi|Hisashi Mitsui
Which Japanese anime film won the Oscar for Best Animated Feature in 2003?|Spirited Away|Princess Mononoke|Your Name|Akira
Who composed the music for most of Miyazaki's films?|Joe Hisaishi|Yoko Kanno|Hiroyuki Sawano|Yuki Kajiura
Who sang "Guren no Yumiya", the Attack on Titan opening?|Linked Horizon|LiSA|Eir Aoi|YOASOBI
Which anime features the song "Unravel"?|Tokyo Ghoul|Bleach|Death Note|Parasyte
In what year did Death Note start airing?|2006|2003|2009|2011
Who is L's elderly assistant in Death Note?|Watari|Roger|Aizawa|Mogi
What is the dog's name in Cowboy Bebop's crew?|Ein|Spike|Bebop|Jet
Which studio produced Kill la Kill?|Studio Trigger|MAPPA|Sunrise|Bones
Which studio produced Monogatari and Puella Magi Madoka Magica?|Shaft|Kyoto Animation|Bones|A-1 Pictures
Which studio produced Sword Art Online?|A-1 Pictures|Ufotable|Madhouse|Bones
Which studio produced Clannad?|Kyoto Animation|Shaft|P.A. Works|Doga Kobo
Which studio produced Haikyuu!!?|Production I.G|Ufotable|Bones|Madhouse
Which studio produced the original 1995 Neon Genesis Evangelion?|Gainax|Madhouse|Sunrise|Studio Ghibli
Who wrote Detective Conan?|Gosho Aoyama|Eiichiro Oda|Hiromu Arakawa|Naoko Takeuchi
Who wrote the Sailor Moon manga?|Naoko Takeuchi|Hiromu Arakawa|Rumiko Takahashi|CLAMP
Who wrote JoJo's Bizarre Adventure?|Hirohiko Araki|Kentaro Miura|Akira Toriyama|Naoki Urasawa
Who wrote the manga Monster?|Naoki Urasawa|Kentaro Miura|Takehiko Inoue|Osamu Tezuka
Who wrote the manga Slam Dunk?|Takehiko Inoue|Naoki Urasawa|Eiichiro Oda|Kentaro Miura
Who wrote the manga Chainsaw Man?|Tatsuki Fujimoto|Gege Akutami|Yuki Tabata|Koyoharu Gotouge
Who is the hero of Steins;Gate?|Rintaro Okabe|Makise Kurisu|Itaru Hashida|Mayuri Shiina
What device sends messages to the past in Steins;Gate?|The Phone Microwave|The golden clock|An hourglass|The old radio
Which 1963 TV anime is considered one of the first modern anime series?|Astro Boy|Speed Racer|Sazae-san|Mazinger Z
Who composed the music for Attack on Titan?|Hiroyuki Sawano|Yoko Kanno|Joe Hisaishi|Yasuharu Takanashi
What is the famous opening song of Cowboy Bebop?|Tank!|Blue Bird|Silhouette|Unravel
In what year did Fullmetal Alchemist: Brotherhood start airing?|2009|2003|2006|2012
In what year did Neon Genesis Evangelion start airing?|1995|1990|1998|2001
In what year did Cowboy Bebop start airing?|1998|1995|2001|2003
In what year did the Naruto manga begin in Weekly Shonen Jump?|1999|1996|2002|2005
In what year was Studio Ghibli founded?|1985|1979|1992|1998
In what year was Spirited Away released?|2001|1999|2003|2005
Who directed Perfect Blue and Paprika?|Satoshi Kon|Hayao Miyazaki|Mamoru Hosoda|Mamoru Oshii
Who wrote Yu Yu Hakusho and Hunter x Hunter?|Yoshihiro Togashi|Masashi Kishimoto|Tite Kubo|Hiromu Arakawa
Who wrote Haikyuu!!?|Haruichi Furudate|Takehiko Inoue|Hiromu Arakawa|Mitsuru Adachi
Who created Grendizer?|Go Nagai|Leiji Matsumoto|Yoshikazu Yasuhiko|Osamu Tezuka
Who wrote the Captain Tsubasa manga?|Yoichi Takahashi|Masashi Kishimoto|Mitsuru Adachi|Rumiko Takahashi
Who directed Grave of the Fireflies?|Isao Takahata|Hayao Miyazaki|Mamoru Hosoda|Makoto Shinkai
Which studio has produced JoJo's Bizarre Adventure since 2012?|David Production|Bones|Pierrot|Sunrise
Which studio produced Mob Psycho 100?|Bones|Madhouse|MAPPA|Trigger
Which studio produced season 2 of Vinland Saga?|MAPPA|Wit Studio|Bones|Madhouse
Which studio produced Your Name?|CoMix Wave Films|Kyoto Animation|Studio Ghibli|Shaft
Which studio produced Solo Leveling?|A-1 Pictures|MAPPA|Ufotable|Wit Studio
Which Miyazaki film won the Oscar for Best Animated Feature at the 2024 ceremony?|The Boy and the Heron|Ponyo|Howl's Moving Castle|The Wind Rises
Who composed the music for Cowboy Bebop?|Yoko Kanno|Joe Hisaishi|Hiroyuki Sawano|Kohei Tanaka
In what year did the original Mobile Suit Gundam start airing?|1979|1985|1969|1990
In what year was the film Akira released?|1988|1982|1991|1995
In what year did the original Sailor Moon start airing?|1992|1989|1996|2000
In what year was My Neighbor Totoro released?|1988|1984|1992|1995
In what year was Princess Mononoke released?|1997|1995|2001|1999
In what year did the Dragon Ball manga begin in Weekly Shonen Jump?|1984|1979|1989|1993
Who directed Ghost in the Shell (1995)?|Mamoru Oshii|Satoshi Kon|Katsuhiro Otomo|Shinichiro Watanabe
Who directed the film Akira?|Katsuhiro Otomo|Mamoru Oshii|Satoshi Kon|Hayao Miyazaki
Who directed Neon Genesis Evangelion?|Hideaki Anno|Shinichiro Watanabe|Makoto Shinkai|Satoshi Kon
Who drew the official One Punch Man manga?|Yusuke Murata|Tatsuki Fujimoto|Takehiko Inoue|Kohei Horikoshi
Who wrote Rurouni Kenshin?|Nobuhiro Watsuki|Kentaro Miura|Tite Kubo|Masashi Kishimoto
Who wrote Hajime no Ippo?|George Morikawa|Takehiko Inoue|Naoki Urasawa|Mitsuru Adachi
Who wrote the story of the Frieren: Beyond Journey's End manga?|Kanehito Yamada|Tsukasa Abe|Gege Akutami|Yuki Tabata
Which studio produced Fate/Zero?|Ufotable|Bones|Madhouse|Trigger
Which studio produced Dandadan?|Science SARU|MAPPA|Trigger|Bones
Which studio produced Oshi no Ko?|Doga Kobo|CloverWorks|Bones|Shaft
Which 1984 Miyazaki film's success led to the founding of Studio Ghibli?|Nausicaä of the Valley of the Wind|Castle in the Sky|My Neighbor Totoro|Kiki's Delivery Service
Which anime is considered one of the first "super robot" anime (1972)?|Mazinger Z|Mobile Suit Gundam|Evangelion|Macross
In which magazine was Berserk published?|Young Animal|Weekly Shonen Jump|Ultra Jump|Afternoon
Who sang "The Rumbling", the opening of Attack on Titan: The Final Season?|SiM|Linked Horizon|LiSA|Eir Aoi
Who voices Goku in the Japanese version?|Masako Nozawa|Megumi Hayashibara|Mayumi Tanaka|Mimiko Iijima
Who directed Cowboy Bebop?|Shinichiro Watanabe|Hideaki Anno|Satoshi Kon|Mamoru Oshii
What was Japan's first color TV anime series (1965)?|Kimba the White Lion|Astro Boy|Speed Racer|Sazae-san
What is the longest-running TV anime of all time?|Sazae-san|Doraemon|Detective Conan|One Piece
Who designed the characters of Neon Genesis Evangelion?|Yoshiyuki Sadamoto|Hideaki Anno|Hayao Miyazaki|Takashi Nakamura
Who created Mobile Suit Gundam?|Yoshiyuki Tomino|Hayao Miyazaki|Go Nagai|Shinichiro Watanabe
Which of these was an early co-founder of Studio Ghibli alongside Miyazaki and Takahata?|Toshio Suzuki|Satoshi Kon|Hideaki Anno|Mamoru Oshii
Who drew the manga Fist of the North Star?|Tetsuo Hara|Takehiko Inoue|Kentaro Miura|Naoki Urasawa
Who created Lupin III?|Monkey Punch|Go Nagai|Osamu Tezuka|Leiji Matsumoto
Who voices Levi Ackerman in the Japanese version?|Hiroshi Kamiya|Yuki Kaji|Mamoru Miyano|Daisuke Ono
In what year did the original Astro Boy start airing?|1963|1958|1969|1972
Who is the hero of Dragon Ball?|Goku|Vegeta|Krillin|Piccolo
What color is Goku's hair when he turns Super Saiyan?|Golden|Red|Blue|Green
What is the name of the lazy boy who owns Doraemon?|Nobita|Suneo|Gian|Shizuka
Where does the heroine of Sailor Moon draw her power from?|The Moon|The Sun|The stars|The sea
Which anime's hero is a boy dreaming of becoming Hokage?|Naruto|One Piece|Bleach|Dragon Ball
What does the word "anime" mean?|Japanese animation|Japanese live-action films|Korean dramas|Comics
What is Goku's famous energy-wave attack called?|Kamehameha|Rasengan|Gomu Gomu|Bankai
What is Naruto's spinning blue sphere of energy called?|Rasengan|Chidori|Kamehameha|Gomu Gomu
Who is the hero of Bleach?|Ichigo Kurosaki|Renji Abarai|Orihime|Chad
Who is the hero of Hunter x Hunter?|Gon Freecss|Killua Zoldyck|Kurapika|Leorio
Who is the hero of Jujutsu Kaisen?|Yuji Itadori|Satoru Gojo|Megumi|Nobara
Who is the hero of Chainsaw Man?|Denji|Power|Aki|Makima
What is the name of Edward Elric's younger brother?|Alphonse|Roy|Hohenheim|Maes
What is the name of the girl who reads minds in Spy x Family?|Anya Forger|Yor Forger|Fiona|Damian
Who is the hero of Black Clover?|Asta|Yuno|Noelle|Yami
Who is the hero of Fairy Tail?|Natsu Dragneel|Gray|Erza|Gajeel
What is the name of the Straw Hat crew's navigator?|Nami|Robin|Vivi|Hancock
What is the name of the reindeer-like doctor on Luffy's crew?|Chopper|Sanji|Usopp|Franky
What is the name of Naruto's pink-haired teammate?|Sakura Haruno|Hinata Hyuga|Ino Yamanaka|Temari
Who is Goku's first teacher, known as the "Turtle Hermit"?|Master Roshi|Piccolo|King Kai|Mr. Popo
Who is Goku's bald friend with no nose?|Krillin|Yamcha|Tien|Gohan
What is Goku's wife's name?|Chi-Chi|Bulma|Mai|Android 18
Who is Vegeta's son?|Trunks|Goten|Gohan|Pan
Who is the hero of Neon Genesis Evangelion?|Shinji Ikari|Kirito|Rintaro Okabe|Eren Yeager
Who is the hero of Code Geass?|Lelouch Lamperouge|Suzaku Kururugi|C.C.|Kallen
Who is the hero of Tokyo Revengers?|Takemichi Hanagaki|Mikey|Draken|Mitsuya
What is the name of the school where the My Hero Academia heroes study?|U.A. High School|Karasuno High|Hogwarts|Konoha Academy
Who wrote the Naruto manga?|Masashi Kishimoto|Eiichiro Oda|Akira Toriyama|Tite Kubo
Who directed Spirited Away?|Hayao Miyazaki|Makoto Shinkai|Isao Takahata|Mamoru Hosoda
Who is the hero of Vinland Saga?|Thorfinn|Thors|Askeladd|Canute
Who is the hero of Cowboy Bebop?|Spike Spiegel|Jet Black|Faye Valentine|Edward
Who is the hero of Mob Psycho 100?|Mob (Shigeo Kageyama)|Reigen|Teruki Hanazawa|Ritsu
Who is the hero of Berserk?|Guts|Griffith|Zodd|Casca
What is Shoyo Hinata's school in Haikyuu!!?|Karasuno|Nekoma|Aoba Johsai|Shiratorizawa
What is the symbol on the Akatsuki cloaks?|Red clouds|A black rose|Blue flames|Green leaves
Who wrote Attack on Titan?|Hajime Isayama|Eiichiro Oda|Masashi Kishimoto|Kentaro Miura
Who wrote Bleach?|Tite Kubo|Masashi Kishimoto|Eiichiro Oda|Akira Toriyama
Who directed Your Name?|Makoto Shinkai|Hayao Miyazaki|Mamoru Hosoda|Satoshi Kon
In what year did Demon Slayer start airing?|2019|2017|2021|2018
In what year did Jujutsu Kaisen start airing?|2020|2018|2022|2021
In what year did Chainsaw Man start airing?|2022|2020|2021|2023
In what year was the film Your Name released?|2016|2013|2018|2019
Who sang "Idol", the Oshi no Ko opening?|YOASOBI|LiSA|Eve|Aimer
Who is the hero of Gintama?|Gintoki Sakata|Shinpachi|Kagura|Hijikata
What is Eren's original power in Attack on Titan?|The Attack Titan|The Founding Titan|The Female Titan|The Armored Titan
What is the famous criminal group in Hunter x Hunter?|The Phantom Troupe|Akatsuki|The Hunters' Guild|The Four Emperors
Which studio produced My Hero Academia?|Bones|Madhouse|MAPPA|Pierrot
Which studio produced Attack on Titan: The Final Season?|MAPPA|Wit Studio|Bones|Ufotable
Who wrote Fullmetal Alchemist?|Hiromu Arakawa|Naoko Takeuchi|Rumiko Takahashi|CLAMP
Who wrote My Hero Academia?|Kohei Horikoshi|Koyoharu Gotouge|Gege Akutami|Tite Kubo
Who wrote Demon Slayer?|Koyoharu Gotouge|Kohei Horikoshi|Gege Akutami|Hajime Isayama
Who wrote Jujutsu Kaisen?|Gege Akutami|Kohei Horikoshi|Tatsuki Fujimoto|Koyoharu Gotouge
Who wrote Doraemon?|Fujiko F. Fujio|Osamu Tezuka|Go Nagai|Akira Toriyama
In what year did My Hero Academia start airing?|2016|2014|2018|2015
Who is the hero of the first part of JoJo's Bizarre Adventure?|Jonathan Joestar|Joseph Joestar|Jotaro Kujo|Josuke Higashikata
Who is the hero of the third part of JoJo's Bizarre Adventure?|Jotaro Kujo|Jonathan Joestar|Joseph Joestar|Josuke Higashikata
Who is the hero of Hajime no Ippo?|Ippo Makunouchi|Takamura|Miyata|Kimura
Who is the hero of Gurren Lagann?|Simon|Kamina|Yoko|Viral
Who is the heroine of Ghost in the Shell?|Major Motoko Kusanagi|Rei Ayanami|Misato|Faye Valentine
Which studio produced Hunter x Hunter (2011)?|Madhouse|Bones|Pierrot|Sunrise
Which studio produced Code Geass?|Sunrise|Madhouse|Bones|Gainax
Who wrote Tokyo Ghoul?|Sui Ishida|Gege Akutami|Hajime Isayama|Tatsuki Fujimoto
Who wrote Black Clover?|Yuki Tabata|Hiro Mashima|Kohei Horikoshi|Tite Kubo
Who wrote Yu-Gi-Oh!?|Kazuki Takahashi|Akira Toriyama|Masashi Kishimoto|Tite Kubo
Who created the original story (webcomic) of One Punch Man?|ONE|Yusuke Murata|Tatsuki Fujimoto|Kohei Horikoshi
In what year did the Naruto anime start airing?|2002|1999|2005|2007
In what year did One Punch Man start airing?|2015|2013|2017|2019
In what year was the film Demon Slayer: Mugen Train released?|2020|2019|2021|2022
Who sang "Kick Back", the Chainsaw Man opening?|Kenshi Yonezu|YOASOBI|Eve|LiSA
Which band composed the music and songs of the film Your Name?|RADWIMPS|LiSA|Aimer|Official HIGE DANdism
Who is the hero of Vagabond?|Miyamoto Musashi|Sasaki Kojiro|Takuan Soho|Matahachi
Who is the hero of Monster?|Kenzo Tenma|Johan Liebert|Heinrich Lunge|Eva Heinemann
Who is the hero of Mushishi?|Ginko|Tama|Tanyuu Karibusa|Adashino
Who is the hero of Clannad?|Tomoya Okazaki|Nagisa Furukawa|Kyou Fujibayashi|Sunohara
Who is the leader of the Phantom Troupe in Hunter x Hunter?|Chrollo Lucilfer|Hisoka|Nobunaga|Phinks
Which friend gained psychic powers in the film Akira?|Tetsuo|Kaneda|Kei|The Colonel
What is the name of Guts's giant sword in Berserk?|Dragonslayer|Masamune|Zangetsu|Kusanagi
Which studio produced Steins;Gate?|White Fox|Madhouse|Bones|A-1 Pictures
Which studio produced Tokyo Ghoul and Black Clover?|Studio Pierrot|Madhouse|Bones|MAPPA
Which studio produced season 1 of One Punch Man?|Madhouse|Bones|MAPPA|Sunrise
Which studio produced Bocchi the Rock!?|CloverWorks|A-1 Pictures|Doga Kobo|P.A. Works
Which two studios co-produced Spy x Family?|Wit Studio and CloverWorks|MAPPA and Bones|Madhouse and Trigger|Ufotable and Shaft
Which studio produced K-On!?|Kyoto Animation|Shaft|P.A. Works|Doga Kobo
Who wrote Fairy Tail?|Hiro Mashima|Yuki Tabata|Eiichiro Oda|Masashi Kishimoto
Who wrote Spy x Family?|Tatsuya Endo|Tatsuki Fujimoto|Gege Akutami|Kohei Horikoshi
Who wrote Vinland Saga?|Makoto Yukimura|Naoki Urasawa|Kentaro Miura|Takehiko Inoue
Who wrote Gintama?|Hideaki Sorachi|Naoki Urasawa|Tite Kubo|Masashi Kishimoto
Who wrote Inuyasha?|Rumiko Takahashi|Naoko Takeuchi|Hiromu Arakawa|CLAMP
Who wrote the story of Death Note?|Tsugumi Ohba|Takeshi Obata|Naoki Urasawa|Tite Kubo
Who drew the Death Note manga?|Takeshi Obata|Tsugumi Ohba|Hiromu Arakawa|Kentaro Miura
In what year did the One Piece anime start airing?|1999|1997|2002|2004
In what year did the One Piece manga begin?|1997|1999|1995|2001
In what year did Dragon Ball Z start airing?|1989|1986|1993|1996
In what year did Detective Conan start airing?|1996|1992|2000|1999
In what year did Bleach start airing?|2004|2002|2007|2009
In what year did Hunter x Hunter (2011 version) start airing?|2011|2009|2013|2014
In what year did Sword Art Online start airing?|2012|2010|2014|2016
In what year did Tokyo Ghoul start airing?|2014|2012|2016|2017
In what year did Steins;Gate start airing?|2011|2009|2013|2015
Who sang "Blue Bird", the Naruto Shippuden opening?|Ikimono-gakari|KANA-BOON|LiSA|Linked Horizon
Who sang "Silhouette", the Naruto Shippuden opening?|KANA-BOON|Ikimono-gakari|Aimer|Eve
Who sang "Again", the Fullmetal Alchemist: Brotherhood opening?|YUI|LiSA|Aimer|Eir Aoi
Who sang "Peace Sign", the My Hero Academia opening?|Kenshi Yonezu|Eve|YOASOBI|Aimer
Who sang "Kaikai Kitan", the Jujutsu Kaisen opening?|Eve|Kenshi Yonezu|LiSA|Aimyon
Who sang "Cha-La Head-Cha-La"?|Hironobu Kageyama|Masatoshi Ono|Hiroyuki Sawano|Kenshi Yonezu
Who composed the music for Demon Slayer together with Go Shiina?|Yuki Kajiura|Yoko Kanno|Joe Hisaishi|Hiroyuki Sawano
Who sang "Crossing Field", the Sword Art Online opening?|LiSA|Eir Aoi|Aimer|ClariS
In what year did the original Dragon Ball start airing?|1986|1984|1989|1991
In what year did Code Geass start airing?|2006|2004|2008|2010
In what year was the film Howl's Moving Castle released?|2004|2001|2006|2008
In what year was the film Kiki's Delivery Service released?|1989|1986|1992|1995
In what year was the film Castle in the Sky released?|1986|1984|1988|1991
Who directed The Girl Who Leapt Through Time (2006)?|Mamoru Hosoda|Makoto Shinkai|Satoshi Kon|Hayao Miyazaki
Who wrote Dr. Stone?|Riichiro Inagaki|Tatsuya Endo|Hiro Mashima|Yuki Tabata
Who wrote the Sword Art Online novels?|Reki Kawahara|Tappei Nagatsuki|Riichiro Inagaki|Koyoharu Gotouge
Who wrote Re:Zero?|Tappei Nagatsuki|Reki Kawahara|Kanehito Yamada|Tatsuya Endo
Who wrote Kuroko no Basket?|Tadatoshi Fujimaki|Haruichi Furudate|Takehiko Inoue|Masashi Kishimoto
Which studio produced Tokyo Revengers?|Liden Films|Wit Studio|Madhouse|Bones
Which studio produced season 1 of The Promised Neverland?|CloverWorks|Wit Studio|Madhouse|Ufotable
Which studio produced Hell's Paradise?|MAPPA|Bones|Madhouse|Trigger
Which studio produced Kaguya-sama: Love is War?|A-1 Pictures|Doga Kobo|Shaft|Kyoto Animation
Which studio produced Hyouka?|Kyoto Animation|Shaft|P.A. Works|Bones
Which studio produced Gintama?|Sunrise|Madhouse|Bones|Pierrot
What is the first opening of Hunter x Hunter (2011)?|Departure!|Gurenge|Tank!|Silhouette
What is the first opening of Death Note?|the WORLD|Tank!|Unravel|Blue Bird
What is the first opening of Naruto?|R★O★C★K★S|Silhouette|Blue Bird|Haruka Kanata
Who directed A Silent Voice (Koe no Katachi)?|Naoko Yamada|Makoto Shinkai|Mamoru Hosoda|Satoshi Kon
Who wrote Soul Eater and Fire Force?|Atsushi Ohkubo|Hiro Mashima|Tite Kubo|Yuki Tabata
Who wrote Gantz?|Hiroya Oku|Hitoshi Iwaaki|Sui Ishida|Kentaro Miura
Who wrote Parasyte (Kiseijuu)?|Hitoshi Iwaaki|Hiroya Oku|Naoki Urasawa|Takehiko Inoue
Who created the Pokémon franchise?|Satoshi Tajiri|Akira Toriyama|Go Nagai|Kazuki Takahashi
Which studio produced Blue Lock?|8bit|MAPPA|Bones|Madhouse
Which studio produced Made in Abyss?|Kinema Citrus|Wit Studio|Madhouse|Bones
Which studio produced Mushishi?|Artland|Kyoto Animation|Madhouse|Bones
In what year was the film Ponyo released?|2008|2004|2011|2013
In what year was the film The Wind Rises released?|2013|2008|2016|2010
What is the first opening of Bleach?|Asterisk|Tank!|Haruka Kanata|Blue Bird
Who sang "Black Catcher", the Black Clover opening?|Vickeblanka|KANA-BOON|Ikimono-gakari|LiSA
What was the first full-length Japanese color anime feature film (1958)?|Hakujaden (The Tale of the White Serpent)|Akira|Astro Boy|Kimba the White Lion
"""


def parse() -> list[tuple[str, list[str]]]:
    out = []
    for line in E_RAW.strip().splitlines():
        parts = [p.strip() for p in line.split("|")]
        assert len(parts) == 5, line
        out.append((parts[0], parts[1:]))
    return out
