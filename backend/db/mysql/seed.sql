-- ============================================================
-- NL2SQL Sakila-Inspired Seed Database (Scaled Up)
-- 16 tables, 2 views, 1000+ rows, rich FK relationships
-- Designed for GNN schema-pruning benchmarks
-- ============================================================
CREATE DATABASE IF NOT EXISTS nl2sql_target;
USE nl2sql_target;

-- Drop tables in FK-safe order
DROP TABLE IF EXISTS payment;
DROP TABLE IF EXISTS rental;
DROP TABLE IF EXISTS inventory;
DROP TABLE IF EXISTS film_category;
DROP TABLE IF EXISTS film_actor;
DROP TABLE IF EXISTS film_text;
DROP TABLE IF EXISTS film;
DROP TABLE IF EXISTS actor;
DROP TABLE IF EXISTS category;
DROP TABLE IF EXISTS language;
DROP TABLE IF EXISTS customer;
DROP TABLE IF EXISTS staff;
DROP TABLE IF EXISTS store;
DROP TABLE IF EXISTS address;
DROP TABLE IF EXISTS city;
DROP TABLE IF EXISTS country;

-- ============================================================
-- 1. COUNTRY
-- ============================================================
CREATE TABLE country (
  country_id   SMALLINT UNSIGNED NOT NULL AUTO_INCREMENT,
  country      VARCHAR(50) NOT NULL,
  last_update  TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (country_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

INSERT INTO country (country) VALUES
('Afghanistan'),('Algeria'),('Argentina'),('Australia'),('Austria'),
('Bangladesh'),('Belgium'),('Bolivia'),('Brazil'),('Canada'),
('Chile'),('China'),('Colombia'),('Czech Republic'),('Denmark'),
('Egypt'),('Estonia'),('Ethiopia'),('Finland'),('France'),
('Germany'),('Greece'),('Hong Kong'),('Hungary'),('India'),
('Indonesia'),('Iran'),('Iraq'),('Ireland'),('Israel'),
('Italy'),('Japan'),('Kenya'),('Latvia'),('Lithuania'),
('Malaysia'),('Mexico'),('Morocco'),('Netherlands'),('New Zealand'),
('Nigeria'),('Norway'),('Pakistan'),('Peru'),('Philippines'),
('Poland'),('Portugal'),('Romania'),('Russia'),('Saudi Arabia'),
('Singapore'),('South Africa'),('South Korea'),('Spain'),('Sweden'),
('Switzerland'),('Taiwan'),('Thailand'),('Turkey'),('Ukraine'),
('United Arab Emirates'),('United Kingdom'),('United States'),('Venezuela'),('Vietnam');

-- ============================================================
-- 2. CITY
-- ============================================================
CREATE TABLE city (
  city_id      SMALLINT UNSIGNED NOT NULL AUTO_INCREMENT,
  city         VARCHAR(50) NOT NULL,
  country_id   SMALLINT UNSIGNED NOT NULL,
  last_update  TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (city_id),
  FOREIGN KEY (country_id) REFERENCES country(country_id) ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

INSERT INTO city (city, country_id) VALUES
-- USA (63)
('New York',63),('Los Angeles',63),('Chicago',63),('Houston',63),('Phoenix',63),
('San Francisco',63),('Seattle',63),('Denver',63),('Boston',63),('Miami',63),
('Atlanta',63),('Dallas',63),('Portland',63),('Las Vegas',63),('Austin',63),
-- UK (62)
('London',62),('Manchester',62),('Birmingham',62),('Liverpool',62),('Edinburgh',62),
-- Canada (10)
('Toronto',10),('Vancouver',10),('Montreal',10),('Ottawa',10),('Calgary',10),
-- India (25)
('Mumbai',25),('Delhi',25),('Bangalore',25),('Chennai',25),('Hyderabad',25),
-- Germany (21)
('Berlin',21),('Munich',21),('Hamburg',21),('Frankfurt',21),('Cologne',21),
-- France (20)
('Paris',20),('Lyon',20),('Marseille',20),('Toulouse',20),('Nice',20),
-- Australia (4)
('Sydney',4),('Melbourne',4),('Brisbane',4),('Perth',4),('Adelaide',4),
-- Japan (32)
('Tokyo',32),('Osaka',32),('Kyoto',32),('Yokohama',32),('Nagoya',32),
-- Brazil (9)
('Sao Paulo',9),('Rio de Janeiro',9),('Brasilia',9),('Salvador',9),('Fortaleza',9),
-- China (12)
('Beijing',12),('Shanghai',12),('Guangzhou',12),('Shenzhen',12),('Chengdu',12),
-- Mexico (37)
('Mexico City',37),('Guadalajara',37),('Monterrey',37),('Puebla',37),('Tijuana',37),
-- Spain (54)
('Madrid',54),('Barcelona',54),('Valencia',54),('Seville',54),('Bilbao',54),
-- Italy (31)
('Rome',31),('Milan',31),('Naples',31),('Turin',31),('Florence',31),
-- South Korea (53)
('Seoul',53),('Busan',53),('Incheon',53),('Daegu',53),('Daejeon',53),
-- Russia (49)
('Moscow',49),('Saint Petersburg',49),('Novosibirsk',49),('Yekaterinburg',49),('Kazan',49),
-- South Africa (52)
('Johannesburg',52),('Cape Town',52),('Durban',52),('Pretoria',52),('Port Elizabeth',52);

-- ============================================================
-- 3. ADDRESS
-- ============================================================
CREATE TABLE address (
  address_id   SMALLINT UNSIGNED NOT NULL AUTO_INCREMENT,
  address      VARCHAR(50) NOT NULL,
  address2     VARCHAR(50) DEFAULT NULL,
  district     VARCHAR(20) NOT NULL,
  city_id      SMALLINT UNSIGNED NOT NULL,
  postal_code  VARCHAR(10) DEFAULT NULL,
  phone        VARCHAR(20) NOT NULL,
  last_update  TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (address_id),
  FOREIGN KEY (city_id) REFERENCES city(city_id) ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

INSERT INTO address (address, district, city_id, postal_code, phone) VALUES
('47 MySakila Drive','Alberta',1,'10001','555-0101'),
('28 MySQL Boulevard','QLD',2,'90001','555-0102'),
('23 Workhaven Lane','Alberta',3,'60601','555-0103'),
('1411 Lillydale Dr','QLD',4,'77001','555-0104'),
('1913 Hanoi Way','Nagasaki',5,'85001','555-0105'),
('692 Joliet Street','Attik',6,'94101','555-0106'),
('1566 Inegl Manor','Mandalay',7,'98101','555-0107'),
('53 Idfu Parkway','Nantou',8,'80201','555-0108'),
('1795 Santiago Way','Texas',9,'02101','555-0109'),
('900 Santiago Drive','Central',10,'33101','555-0110'),
('478 Joliet Way','Hamilton',11,'30301','555-0111'),
('613 Korolev Drive','Masqat',12,'75201','555-0112'),
('1531 Sal Drive','Rawalpindi',13,'97201','555-0113'),
('1325 Fukuyama Str','Heilongjiang',14,'89101','555-0114'),
('1688 Okara Way','Nothwest',15,'78701','555-0115'),
('262 A Corua Dr','Dhaka',16,'EC1A','555-0116'),
('28 Charlotte Way','Manitoba',17,'M1 1AA','555-0117'),
('1780 Hino Drive','Bur Said',18,'B1 1AA','555-0118'),
('1515 Korla Way','England',19,'L1 1AA','555-0119'),
('1367 Yantai Drive','Serrana',20,'EH1 1AA','555-0120'),
('519 Brescia Ave','Ontario',21,'M5V 2T6','555-0121'),
('1768 Udine Parkway','BC',22,'V5K 2A1','555-0122'),
('1150 Kimchon Pkwy','Quebec',23,'H2X 1Y4','555-0123'),
('270 Amuq Walk','Ottawa',24,'K1A 0B1','555-0124'),
('770 Bydgoszcz Ave','AB',25,'T2P 1J9','555-0125'),
('419 Iligan Lane','Maharashtra',26,'400001','555-0126'),
('138 Dhaka Way','Delhi',27,'110001','555-0127'),
('793 Cam Ranh Ave','Karnataka',28,'560001','555-0128'),
('1166 Changhwa Rd','TN',29,'600001','555-0129'),
('1325 Purwakarta Way','AP',30,'500001','555-0130'),
('688 Ghaziabad Lane','Brandenburg',31,'10115','555-0131'),
('679 Athenai Walk','Bavaria',32,'80331','555-0132'),
('1426 Tabuk Place','Hamburg',33,'20095','555-0133'),
('587 Benguela Manor','Hessen',34,'60311','555-0134'),
('430 Kumbakonam Dr','NRW',35,'50667','555-0135'),
('1888 Kabul Lane','Paris',36,'75001','555-0136'),
('390 Wroclaw Way','Rhone',37,'69001','555-0137'),
('1368 Maracabo Ave','BDR',38,'13001','555-0138'),
('869 Shikarpur Way','HauteGaronne',39,'31000','555-0139'),
('1027 Songkhla Manor','AlpesMaritimes',40,'06000','555-0140'),
('671 Belo Horizonte','NSW',41,'2000','555-0141'),
('588 Vila Velha Ave','Victoria',42,'3000','555-0142'),
('1489 Kakamigahara','QLD',43,'4000','555-0143'),
('1076 Salon de Pr','WA',44,'6000','555-0144'),
('531 Malatya Ave','SA',45,'5000','555-0145'),
('442 Rae Bareli Lane','Kanto',46,'1000001','555-0146'),
('1157 Nyeri Way','Osaka',47,'5300001','555-0147'),
('1631 Tabriz Ave','Kyoto',48,'6000001','555-0148'),
('886 Olomouc Pkwy','Kanagawa',49,'2200001','555-0149'),
('1325 Belem Place','Aichi',50,'4600001','555-0150'),
('1795 Korolev Drive','SP',51,'01000','555-0151'),
('1913 Kamakura Place','RJ',52,'20000','555-0152'),
('1531 Brest Drive','DF',53,'70000','555-0153'),
('1325 Aparecida Way','BA',54,'40000','555-0154'),
('1688 Jining Ave','CE',55,'60000','555-0155'),
('262 Paarl Lane','Hebei',56,'100000','555-0156'),
('28 Tabriz Ave','Shanghai',57,'200000','555-0157'),
('1780 Guangzhou St','GD',58,'510000','555-0158'),
('1515 Shenzhen Rd','GD',59,'518000','555-0159'),
('1367 Chengdu Pkwy','Sichuan',60,'610000','555-0160'),
('519 Aguascalientes','DF',61,'06600','555-0161'),
('1768 Celaya Way','Jalisco',62,'44100','555-0162'),
('1150 Monterrey St','NuevoLeon',63,'64000','555-0163'),
('270 Puebla Lane','Puebla',64,'72000','555-0164'),
('770 Tijuana Pkwy','BC',65,'22000','555-0165'),
('1180 Madrid Blvd','Madrid',66,'28001','555-0166'),
('455 Barcelona Ave','Catalonia',67,'08001','555-0167'),
('900 Valencia Dr','Valencia',68,'46001','555-0168'),
('378 Seville Lane','Andalusia',69,'41001','555-0169'),
('220 Bilbao Place','Basque',70,'48001','555-0170'),
('651 Rome Street','Lazio',71,'00100','555-0171'),
('890 Milan Blvd','Lombardy',72,'20100','555-0172'),
('231 Naples Way','Campania',73,'80100','555-0173'),
('567 Turin Place','Piedmont',74,'10100','555-0174'),
('432 Florence Ave','Tuscany',75,'50100','555-0175'),
('880 Seoul Blvd','Gyeonggi',76,'03000','555-0176'),
('120 Busan Drive','Busan',77,'46000','555-0177'),
('345 Incheon Lane','Incheon',78,'21000','555-0178'),
('678 Daegu Place','TG',79,'41000','555-0179'),
('901 Daejeon Street','DJ',80,'34000','555-0180'),
('543 Moscow Blvd','Moscow',81,'101000','555-0181'),
('765 StPete Ave','StPete',82,'190000','555-0182'),
('321 Novo Way','NSO',83,'630000','555-0183'),
('876 Yekat Drive','Sverdlovsk',84,'620000','555-0184'),
('234 Kazan Lane','Tatarstan',85,'420000','555-0185'),
('111 Joburg Street','Gauteng',86,'2000','555-0186'),
('222 CapeTown Ave','WCape',87,'8000','555-0187'),
('333 Durban Blvd','KZN',88,'4000','555-0188'),
('444 Pretoria Dr','Gauteng',89,'0001','555-0189'),
('555 PE Way','ECape',90,'6001','555-0190');

-- ============================================================
-- 4. STORE
-- ============================================================
CREATE TABLE store (
  store_id         TINYINT UNSIGNED NOT NULL AUTO_INCREMENT,
  manager_staff_id TINYINT UNSIGNED DEFAULT NULL,
  address_id       SMALLINT UNSIGNED NOT NULL,
  last_update      TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (store_id),
  FOREIGN KEY (address_id) REFERENCES address(address_id) ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

INSERT INTO store (manager_staff_id, address_id) VALUES
(NULL, 1), (NULL, 16), (NULL, 31), (NULL, 46), (NULL, 61);

-- ============================================================
-- 5. STAFF
-- ============================================================
CREATE TABLE staff (
  staff_id    TINYINT UNSIGNED NOT NULL AUTO_INCREMENT,
  first_name  VARCHAR(45) NOT NULL,
  last_name   VARCHAR(45) NOT NULL,
  address_id  SMALLINT UNSIGNED NOT NULL,
  email       VARCHAR(50) DEFAULT NULL,
  store_id    TINYINT UNSIGNED NOT NULL,
  active      BOOLEAN NOT NULL DEFAULT TRUE,
  username    VARCHAR(16) NOT NULL,
  last_update TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (staff_id),
  FOREIGN KEY (store_id) REFERENCES store(store_id) ON UPDATE CASCADE,
  FOREIGN KEY (address_id) REFERENCES address(address_id) ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

INSERT INTO staff (first_name, last_name, address_id, email, store_id, username) VALUES
('Mike','Hillyer',1,'mike.hillyer@sakilastaff.com',1,'Mike'),
('Jon','Stephens',2,'jon.stephens@sakilastaff.com',2,'Jon'),
('Sarah','Connor',3,'sarah.connor@sakilastaff.com',1,'Sarah'),
('James','Kirk',4,'james.kirk@sakilastaff.com',2,'James'),
('Diana','Prince',5,'diana.prince@sakilastaff.com',3,'Diana'),
('Bruce','Wayne',6,'bruce.wayne@sakilastaff.com',3,'Bruce'),
('Clark','Kent',7,'clark.kent@sakilastaff.com',4,'Clark'),
('Peter','Parker',8,'peter.parker@sakilastaff.com',4,'Peter'),
('Tony','Stark',9,'tony.stark@sakilastaff.com',5,'Tony'),
('Natasha','Romanoff',10,'natasha.romanoff@sakilastaff.com',5,'Natasha');

-- Set managers
UPDATE store SET manager_staff_id = 1 WHERE store_id = 1;
UPDATE store SET manager_staff_id = 2 WHERE store_id = 2;
UPDATE store SET manager_staff_id = 5 WHERE store_id = 3;
UPDATE store SET manager_staff_id = 7 WHERE store_id = 4;
UPDATE store SET manager_staff_id = 9 WHERE store_id = 5;

-- ============================================================
-- 6. CUSTOMER (150 customers across 5 stores)
-- ============================================================
CREATE TABLE customer (
  customer_id  SMALLINT UNSIGNED NOT NULL AUTO_INCREMENT,
  store_id     TINYINT UNSIGNED NOT NULL,
  first_name   VARCHAR(45) NOT NULL,
  last_name    VARCHAR(45) NOT NULL,
  email        VARCHAR(50) DEFAULT NULL,
  address_id   SMALLINT UNSIGNED NOT NULL,
  active       BOOLEAN NOT NULL DEFAULT TRUE,
  create_date  DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  last_update  TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (customer_id),
  FOREIGN KEY (store_id) REFERENCES store(store_id) ON UPDATE CASCADE,
  FOREIGN KEY (address_id) REFERENCES address(address_id) ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

INSERT INTO customer (store_id, first_name, last_name, email, address_id, create_date) VALUES
-- Store 1 (30 customers)
(1,'Mary','Smith','mary.smith@sakilacustomer.org',1,'2022-02-14'),
(1,'Patricia','Johnson','patricia.johnson@sakilacustomer.org',2,'2022-02-14'),
(1,'Linda','Williams','linda.williams@sakilacustomer.org',3,'2022-02-14'),
(1,'Barbara','Jones','barbara.jones@sakilacustomer.org',4,'2022-03-01'),
(1,'Elizabeth','Brown','elizabeth.brown@sakilacustomer.org',5,'2022-03-01'),
(1,'Jennifer','Davis','jennifer.davis@sakilacustomer.org',6,'2022-03-15'),
(1,'Maria','Miller','maria.miller@sakilacustomer.org',7,'2022-04-01'),
(1,'Susan','Wilson','susan.wilson@sakilacustomer.org',8,'2022-04-01'),
(1,'Margaret','Moore','margaret.moore@sakilacustomer.org',9,'2022-04-15'),
(1,'Dorothy','Taylor','dorothy.taylor@sakilacustomer.org',10,'2022-05-01'),
(1,'Lisa','Anderson','lisa.anderson@sakilacustomer.org',11,'2022-05-01'),
(1,'Nancy','Thomas','nancy.thomas@sakilacustomer.org',12,'2022-05-15'),
(1,'Karen','Jackson','karen.jackson@sakilacustomer.org',13,'2022-06-01'),
(1,'Betty','White','betty.white@sakilacustomer.org',14,'2022-06-01'),
(1,'Helen','Harris','helen.harris@sakilacustomer.org',15,'2022-06-15'),
(1,'Sandra','Martin','sandra.martin@sakilacustomer.org',1,'2022-07-01'),
(1,'Donna','Thompson','donna.thompson@sakilacustomer.org',2,'2022-07-01'),
(1,'Carol','Garcia','carol.garcia@sakilacustomer.org',3,'2022-07-15'),
(1,'Ruth','Martinez','ruth.martinez@sakilacustomer.org',4,'2022-08-01'),
(1,'Sharon','Robinson','sharon.robinson@sakilacustomer.org',5,'2022-08-01'),
(1,'Oscar','Wilde','oscar.wilde@sakilacustomer.org',6,'2022-08-15'),
(1,'Ernest','Hemingway','ernest.hemingway@sakilacustomer.org',7,'2022-09-01'),
(1,'Mark','Twain','mark.twain@sakilacustomer.org',8,'2022-09-01'),
(1,'Charles','Dickens','charles.dickens@sakilacustomer.org',9,'2022-09-15'),
(1,'William','Shakespeare','william.shakespeare@sakilacustomer.org',10,'2022-10-01'),
(1,'Robert','Frost','robert.frost@sakilacustomer.org',11,'2022-10-01'),
(1,'Walt','Whitman','walt.whitman@sakilacustomer.org',12,'2022-10-15'),
(1,'Edgar','Poe','edgar.poe@sakilacustomer.org',13,'2022-11-01'),
(1,'Herman','Melville','herman.melville@sakilacustomer.org',14,'2022-11-01'),
(1,'Nathaniel','Hawthorne','nathaniel.hawthorne@sakilacustomer.org',15,'2022-11-15'),
-- Store 2 (30 customers)
(2,'Michelle','Clark','michelle.clark@sakilacustomer.org',16,'2022-02-14'),
(2,'Laura','Rodriguez','laura.rodriguez@sakilacustomer.org',17,'2022-02-14'),
(2,'Sarah','Lewis','sarah.lewis@sakilacustomer.org',18,'2022-02-14'),
(2,'Kimberly','Lee','kimberly.lee@sakilacustomer.org',19,'2022-03-01'),
(2,'Deborah','Walker','deborah.walker@sakilacustomer.org',20,'2022-03-01'),
(2,'Jessica','Hall','jessica.hall@sakilacustomer.org',21,'2022-03-15'),
(2,'Shirley','Allen','shirley.allen@sakilacustomer.org',22,'2022-04-01'),
(2,'Cynthia','Young','cynthia.young@sakilacustomer.org',23,'2022-04-01'),
(2,'Angela','Hernandez','angela.hernandez@sakilacustomer.org',24,'2022-04-15'),
(2,'Melissa','King','melissa.king@sakilacustomer.org',25,'2022-05-01'),
(2,'Brenda','Wright','brenda.wright@sakilacustomer.org',26,'2022-05-01'),
(2,'Amy','Lopez','amy.lopez@sakilacustomer.org',27,'2022-05-15'),
(2,'Anna','Hill','anna.hill@sakilacustomer.org',28,'2022-06-01'),
(2,'Rebecca','Scott','rebecca.scott@sakilacustomer.org',29,'2022-06-01'),
(2,'Virginia','Green','virginia.green@sakilacustomer.org',30,'2022-06-15'),
(2,'Kathleen','Adams','kathleen.adams@sakilacustomer.org',16,'2022-07-01'),
(2,'Pamela','Baker','pamela.baker@sakilacustomer.org',17,'2022-07-01'),
(2,'Martha','Gonzalez','martha.gonzalez@sakilacustomer.org',18,'2022-07-15'),
(2,'Debra','Nelson','debra.nelson@sakilacustomer.org',19,'2022-08-01'),
(2,'Amanda','Carter','amanda.carter@sakilacustomer.org',20,'2022-08-01'),
(2,'Jane','Austen','jane.austen@sakilacustomer.org',21,'2022-08-15'),
(2,'Leo','Tolstoy','leo.tolstoy@sakilacustomer.org',22,'2022-09-01'),
(2,'Fyodor','Dostoevsky','fyodor.dostoevsky@sakilacustomer.org',23,'2022-09-01'),
(2,'Victor','Hugo','victor.hugo@sakilacustomer.org',24,'2022-09-15'),
(2,'Gabriel','Marquez','gabriel.marquez@sakilacustomer.org',25,'2022-10-01'),
(2,'Alexandre','Dumas','alexandre.dumas@sakilacustomer.org',26,'2022-10-01'),
(2,'Jules','Verne','jules.verne@sakilacustomer.org',27,'2022-10-15'),
(2,'Honore','Balzac','honore.balzac@sakilacustomer.org',28,'2022-11-01'),
(2,'Gustave','Flaubert','gustave.flaubert@sakilacustomer.org',29,'2022-11-01'),
(2,'Marcel','Proust','marcel.proust@sakilacustomer.org',30,'2022-11-15'),
-- Store 3 (30 customers)
(3,'Stephanie','Mitchell','stephanie.mitchell@sakilacustomer.org',31,'2022-02-14'),
(3,'Carolyn','Perez','carolyn.perez@sakilacustomer.org',32,'2022-02-14'),
(3,'Christine','Roberts','christine.roberts@sakilacustomer.org',33,'2022-03-01'),
(3,'Marie','Turner','marie.turner@sakilacustomer.org',34,'2022-03-01'),
(3,'Janet','Phillips','janet.phillips@sakilacustomer.org',35,'2022-03-15'),
(3,'Catherine','Campbell','catherine.campbell@sakilacustomer.org',36,'2022-04-01'),
(3,'Frances','Parker','frances.parker@sakilacustomer.org',37,'2022-04-01'),
(3,'Ann','Evans','ann.evans@sakilacustomer.org',38,'2022-04-15'),
(3,'Joyce','Edwards','joyce.edwards@sakilacustomer.org',39,'2022-05-01'),
(3,'Diane','Collins','diane.collins@sakilacustomer.org',40,'2022-05-01'),
(3,'Alice','Stewart','alice.stewart@sakilacustomer.org',41,'2022-05-15'),
(3,'Julie','Sanchez','julie.sanchez@sakilacustomer.org',42,'2022-06-01'),
(3,'Heather','Morris','heather.morris@sakilacustomer.org',43,'2022-06-01'),
(3,'Teresa','Rogers','teresa.rogers@sakilacustomer.org',44,'2022-06-15'),
(3,'Doris','Reed','doris.reed@sakilacustomer.org',45,'2022-07-01'),
(3,'Franz','Kafka','franz.kafka@sakilacustomer.org',31,'2022-07-01'),
(3,'Jorge','Borges','jorge.borges@sakilacustomer.org',32,'2022-07-15'),
(3,'Haruki','Murakami','haruki.murakami@sakilacustomer.org',33,'2022-08-01'),
(3,'Albert','Camus','albert.camus@sakilacustomer.org',34,'2022-08-01'),
(3,'George','Orwell','george.orwell@sakilacustomer.org',35,'2022-08-15'),
(3,'Thomas','Mann','thomas.mann@sakilacustomer.org',36,'2022-09-01'),
(3,'Hermann','Hesse','hermann.hesse@sakilacustomer.org',37,'2022-09-01'),
(3,'Gunter','Grass','gunter.grass@sakilacustomer.org',38,'2022-09-15'),
(3,'Bertolt','Brecht','bertolt.brecht@sakilacustomer.org',39,'2022-10-01'),
(3,'Rainer','Rilke','rainer.rilke@sakilacustomer.org',40,'2022-10-01'),
-- Store 4 (30 customers)
(4,'Katherine','Rivera','katherine.rivera@sakilacustomer.org',46,'2022-02-14'),
(4,'Joan','Cooper','joan.cooper@sakilacustomer.org',47,'2022-02-14'),
(4,'Judith','Richardson','judith.richardson@sakilacustomer.org',48,'2022-03-01'),
(4,'Rose','Cox','rose.cox@sakilacustomer.org',49,'2022-03-01'),
(4,'Janice','Howard','janice.howard@sakilacustomer.org',50,'2022-03-15'),
(4,'Kelly','Ward','kelly.ward@sakilacustomer.org',51,'2022-04-01'),
(4,'Nicole','Torres','nicole.torres@sakilacustomer.org',52,'2022-04-01'),
(4,'Judy','Peterson','judy.peterson@sakilacustomer.org',53,'2022-04-15'),
(4,'Christina','Gray','christina.gray@sakilacustomer.org',54,'2022-05-01'),
(4,'Kathy','Ramirez','kathy.ramirez@sakilacustomer.org',55,'2022-05-01'),
(4,'Theresa','James','theresa.james@sakilacustomer.org',46,'2022-05-15'),
(4,'Beverly','Watson','beverly.watson@sakilacustomer.org',47,'2022-06-01'),
(4,'Denise','Brooks','denise.brooks@sakilacustomer.org',48,'2022-06-01'),
(4,'Tammy','Kelly','tammy.kelly@sakilacustomer.org',49,'2022-06-15'),
(4,'Irene','Sanders','irene.sanders@sakilacustomer.org',50,'2022-07-01'),
(4,'Agatha','Christie','agatha.christie@sakilacustomer.org',51,'2022-07-01'),
(4,'Arthur','Doyle','arthur.doyle@sakilacustomer.org',52,'2022-07-15'),
(4,'Stephen','King','stephen.king@sakilacustomer.org',53,'2022-08-01'),
(4,'Isaac','Asimov','isaac.asimov@sakilacustomer.org',54,'2022-08-01'),
(4,'Ray','Bradbury','ray.bradbury@sakilacustomer.org',55,'2022-08-15'),
(4,'Yukio','Mishima','yukio.mishima@sakilacustomer.org',46,'2022-09-01'),
(4,'Natsume','Soseki','natsume.soseki@sakilacustomer.org',47,'2022-09-01'),
(4,'Banana','Yoshimoto','banana.yoshimoto@sakilacustomer.org',48,'2022-09-15'),
(4,'Kenji','Miyazawa','kenji.miyazawa@sakilacustomer.org',49,'2022-10-01'),
(4,'Ryunosuke','Akutagawa','ryunosuke.akutagawa@sakilacustomer.org',50,'2022-10-01'),
-- Store 5 (30 customers)
(5,'Kathryn','Henderson','kathryn.henderson@sakilacustomer.org',61,'2022-02-14'),
(5,'Louise','Coleman','louise.coleman@sakilacustomer.org',62,'2022-02-14'),
(5,'Sara','Jenkins','sara.jenkins@sakilacustomer.org',63,'2022-03-01'),
(5,'Anne','Perry','anne.perry@sakilacustomer.org',64,'2022-03-01'),
(5,'Jacqueline','Powell','jacqueline.powell@sakilacustomer.org',65,'2022-03-15'),
(5,'Wanda','Long','wanda.long@sakilacustomer.org',66,'2022-04-01'),
(5,'Bonnie','Patterson','bonnie.patterson@sakilacustomer.org',67,'2022-04-01'),
(5,'Julia','Hughes','julia.hughes@sakilacustomer.org',68,'2022-04-15'),
(5,'Ruby','Flores','ruby.flores@sakilacustomer.org',69,'2022-05-01'),
(5,'Tina','Washington','tina.washington@sakilacustomer.org',70,'2022-05-01'),
(5,'Lois','Butler','lois.butler@sakilacustomer.org',71,'2022-05-15'),
(5,'Phyllis','Simmons','phyllis.simmons@sakilacustomer.org',72,'2022-06-01'),
(5,'Norma','Foster','norma.foster@sakilacustomer.org',73,'2022-06-01'),
(5,'Paula','Gonzales','paula.gonzales@sakilacustomer.org',74,'2022-06-15'),
(5,'Diana','Bryant','diana.bryant@sakilacustomer.org',75,'2022-07-01'),
(5,'Toni','Morrison','toni.morrison@sakilacustomer.org',61,'2022-07-01'),
(5,'Maya','Angelou','maya.angelou@sakilacustomer.org',62,'2022-07-15'),
(5,'Virginia','Woolf','virginia.woolf@sakilacustomer.org',63,'2022-08-01'),
(5,'Sylvia','Plath','sylvia.plath@sakilacustomer.org',64,'2022-08-01'),
(5,'Emily','Bronte','emily.bronte@sakilacustomer.org',65,'2022-08-15'),
(5,'Pablo','Neruda','pablo.neruda@sakilacustomer.org',66,'2022-09-01'),
(5,'Isabel','Allende','isabel.allende@sakilacustomer.org',67,'2022-09-01'),
(5,'Carlos','Fuentes','carlos.fuentes@sakilacustomer.org',68,'2022-09-15'),
(5,'Julio','Cortazar','julio.cortazar@sakilacustomer.org',69,'2022-10-01'),
(5,'Mario','Llosa','mario.llosa@sakilacustomer.org',70,'2022-10-01');

-- ============================================================
-- 7. LANGUAGE
-- ============================================================
CREATE TABLE language (
  language_id  TINYINT UNSIGNED NOT NULL AUTO_INCREMENT,
  name         CHAR(20) NOT NULL,
  last_update  TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (language_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

INSERT INTO language (name) VALUES
('English'),('Italian'),('Japanese'),('Mandarin'),('French'),
('German'),('Spanish'),('Korean'),('Portuguese'),('Hindi'),
('Russian'),('Arabic'),('Turkish'),('Polish'),('Dutch');

-- ============================================================
-- 8. CATEGORY
-- ============================================================
CREATE TABLE category (
  category_id  TINYINT UNSIGNED NOT NULL AUTO_INCREMENT,
  name         VARCHAR(25) NOT NULL,
  last_update  TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (category_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

INSERT INTO category (name) VALUES
('Action'),('Animation'),('Children'),('Classics'),('Comedy'),
('Documentary'),('Drama'),('Family'),('Foreign'),('Games'),
('Horror'),('Music'),('New'),('Sci-Fi'),('Sports'),('Travel');

-- ============================================================
-- 9. ACTOR (160 actors)
-- ============================================================
CREATE TABLE actor (
  actor_id     SMALLINT UNSIGNED NOT NULL AUTO_INCREMENT,
  first_name   VARCHAR(45) NOT NULL,
  last_name    VARCHAR(45) NOT NULL,
  last_update  TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (actor_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

INSERT INTO actor (first_name, last_name) VALUES
('Penelope','Guiness'),('Nick','Wahlberg'),('Ed','Chase'),('Jennifer','Davis'),
('Johnny','Lollobrigida'),('Bette','Nicholson'),('Grace','Mostel'),('Matthew','Johansson'),
('Joe','Swank'),('Christian','Gable'),('Zero','Cage'),('Karl','Berry'),
('Uma','Wood'),('Vivien','Bergen'),('Cuba','Olivier'),('Fred','Costner'),
('Helen','Voight'),('Dan','Torn'),('Bob','Fawcett'),('Lucille','Tracy'),
('Kirsten','Paltrow'),('Elvis','Marx'),('Sandra','Kilmer'),('Cameron','Streep'),
('Kevin','Bloom'),('Rip','Crawford'),('Julia','Mcqueen'),('Woody','Hoffman'),
('Alec','Wayne'),('Sandra','Peck'),('Sissy','Sobieski'),('Tim','Hackman'),
('Milla','Peck'),('Audrey','Olivier'),('Judy','Dean'),('Burt','Dukakis'),
('Val','Bolger'),('Tom','Mckellen'),('Goldie','Brody'),('Johnny','Cage'),
('Jodie','Degeneres'),('Tom','Miranda'),('Kirk','Jovovich'),('Nick','Degeneres'),
('Reese','Kilmer'),('Parker','Goldberg'),('Julia','Barrymore'),('Frances','Day-Lewis'),
('Anne','Cronyn'),('Natalie','Hopkins'),('Gary','Phoenix'),('Carmen','Hunt'),
('Mena','Temple'),('Penelope','Pinkett'),('Fay','Kilmer'),('Dan','Harris'),
('Jude','Cruise'),('Christian','Akroyd'),('Minnie','Zellweger'),('Chris','Depp'),
('Sissy','Williams'),('Sean','Guiness'),('Humphrey','Garland'),('Al','Garland'),
('Kim','Allen'),('Julia','Zellweger'),('Meryl','Gibson'),('Jessica','Bailey'),
('Spencer','Peck'),('Gina','Degeneres'),('Woody','Allen'),('Adam','Grant'),
('Renee','Ball'),('Kirk','Winslet'),('Adam','Hopper'),('Cuba','Birch'),
('Groucho','Dunst'),('Scarlett','Bening'),('Woody','Jolie'),('Ben','Willis'),
('James','Pitt'),('Minnie','Kilmer'),('Chris','Berry'),('Mena','Hopper'),
('Morgan','Williams'),('Lucille','Dee'),('Cuba','Allen'),('Penelope','Monroe'),
('Scarlett','Damon'),('Groucho','Sinatra'),('Matthew','Leigh'),('Kevin','Garland'),
('Rick','Penn'),('Russell','Close'),('Humphrey','Willis'),('Ed','Mansfield'),
('Albert','Nolte'),('Groucho','Williams'),('Adam','Sandler'),('Gary','Streep'),
('Morgan','Hopkins'),('Gene','Willis'),('Burt','Temple'),('Meryl','Allen'),
('Jayne','Nolte'),('Bela','Walken'),('Reese','West'),('Mary','Keitel'),
('Burt','Posey'),('Sandra','Gable'),('Lucille','Dench'),('Thora','Temple'),
('Renee','Tracy'),('Scarlett','Johansson'),('Rock','Dukakis'),('Groucho','Fawcett'),
('Karl','Streep'),('Fay','Wood'),('Russell','Temple'),('Kenneth','Pesci'),
('Greta','Keitel'),('Vivien','Basinger'),('River','Dean'),('Angela','Hudson'),
('Russell','Bacall'),('Salma','Nolte'),('Scarlett','West'),('Daryl','Wahlberg'),
('Gene','Hopkins'),('Spencer','Depp'),('Kenneth','Hoffman'),('Mena','Temple'),
('Woody','Garland'),('Laura','Brody'),('Audrey','Bailey'),('Jada','Ryder'),
('Cameron','Wray'),('Gene','Hackman'),('Jada','Ben'),('Rock','Allen'),
('Matthew','Carrey'),('Penelope','Cronyn'),('Gene','Mckellen'),('Burt','Jackman'),
('Leonardo','DiCaprio'),('Robert','DeNiro'),('Cate','Blanchett'),('Matt','Damon'),
('Nicole','Kidman'),('Hugh','Jackman'),('Will','Smith'),('Denzel','Washington'),
('Morgan','Freeman'),('Halle','Berry'),('Jennifer','Lawrence'),('Chris','Evans'),
('Ryan','Gosling'),('Emma','Stone'),('Chris','Hemsworth'),('Margot','Robbie');

-- ============================================================
-- 10. FILM (65 films)
-- ============================================================
CREATE TABLE film (
  film_id              SMALLINT UNSIGNED NOT NULL AUTO_INCREMENT,
  title                VARCHAR(128) NOT NULL,
  description          TEXT DEFAULT NULL,
  release_year         YEAR DEFAULT NULL,
  language_id          TINYINT UNSIGNED NOT NULL,
  original_language_id TINYINT UNSIGNED DEFAULT NULL,
  rental_duration      TINYINT UNSIGNED NOT NULL DEFAULT 3,
  rental_rate          DECIMAL(4,2) NOT NULL DEFAULT 4.99,
  length               SMALLINT UNSIGNED DEFAULT NULL,
  replacement_cost     DECIMAL(5,2) NOT NULL DEFAULT 19.99,
  rating               ENUM('G','PG','PG-13','R','NC-17') DEFAULT 'G',
  special_features     SET('Trailers','Commentaries','Deleted Scenes','Behind the Scenes') DEFAULT NULL,
  last_update          TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (film_id),
  FOREIGN KEY (language_id) REFERENCES language(language_id) ON UPDATE CASCADE,
  FOREIGN KEY (original_language_id) REFERENCES language(language_id) ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

INSERT INTO film (title, description, release_year, language_id, original_language_id, rental_duration, rental_rate, length, replacement_cost, rating, special_features) VALUES
('ACADEMY DINOSAUR','A Epic Drama of a Feminist And a Mad Scientist who must Battle a Teacher in The Canadian Rockies',2006,1,NULL,6,0.99,86,20.99,'PG','Deleted Scenes,Behind the Scenes'),
('ACE GOLDFINGER','A Astounding Epistle of a Database Administrator And a Explorer who must Find a Car in Ancient China',2006,1,NULL,3,4.99,48,12.99,'G','Trailers'),
('ADAPTATION HOLES','A Astounding Reflection of a Lumberjack And a Car who must Sink a Lumberjack in A Baloon Factory',2006,1,NULL,7,2.99,50,18.99,'NC-17','Trailers,Deleted Scenes'),
('AFFAIR PREJUDICE','A Feckless Documentary of a Frisbee And a Lumberjack who must Chase a Monkey in A Shark Tank',2006,1,NULL,5,2.99,117,26.99,'G','Commentaries,Behind the Scenes'),
('AFRICAN EGG','A Fast-Paced Documentary of a Pastry Chef And a Dentist who must Pursue a Forensic Psychologist in The Gulf of Mexico',2006,1,NULL,6,2.99,130,22.99,'G','Deleted Scenes'),
('AGENT TRUMAN','A Intrepid Panorama of a Robot And a Boy who must Escape a Sumo Wrestler in Ancient China',2006,1,NULL,3,2.99,169,17.99,'PG','Deleted Scenes'),
('AIRPLANE SIERRA','A Touching Saga of a Hunter And a Butler who must Discover a Butler in A Jet Boat',2006,1,NULL,6,4.99,62,28.99,'PG-13','Trailers,Deleted Scenes'),
('AIRPORT POLLOCK','A Epic Tale of a Moose And a Girl who must Confront a Monkey in Ancient India',2006,1,NULL,6,4.99,54,15.99,'R','Trailers'),
('ALABAMA DEVIL','A Thoughtful Panorama of a Database Administrator And a Husband who must Overcome a Mad Scientist in A Jet Boat',2006,1,NULL,3,2.99,114,21.99,'PG-13','Trailers,Deleted Scenes'),
('ALADDIN CALENDAR','A Action-Packed Tale of a Man And a Lumberjack who must Reach a Feminist in Ancient China',2006,1,NULL,6,4.99,63,24.99,'NC-17','Trailers,Deleted Scenes'),
('ALAMO VIDEOTAPE','A Boring Epistle of a Butler And a Cat who must Fight a Pastry Chef in A MySQL Convention',2006,1,NULL,6,0.99,126,16.99,'G','Commentaries,Behind the Scenes'),
('ALASKA PHANTOM','A Feckless Saga of a Hunter And a Pastry Chef who must Vanquish a Boy in Australia',2006,1,NULL,6,0.99,136,22.99,'PG','Commentaries,Deleted Scenes'),
('ALICE FANTASIA','A Emotional Drama of a A Shark And a Database Administrator who must Vanquish a Pioneer in Soviet Georgia',2006,1,NULL,6,0.99,94,23.99,'NC-17','Trailers,Deleted Scenes,Behind the Scenes'),
('ALIEN CENTER','A Brilliant Drama of a Cat And a Mad Scientist who must Battle a Feminist in A MySQL Convention',2006,1,NULL,5,2.99,46,21.99,'NC-17','Trailers,Commentaries,Behind the Scenes'),
('ALLEY EVOLUTION','A Fast-Paced Drama of a Robot And a Composer who must Battle a Astronaut in New Orleans',2006,1,NULL,6,2.99,180,23.99,'NC-17','Trailers,Commentaries'),
('ALONE TRIP','A Fast-Paced Character Study of a Composer And a Dog who must Outgun a Boat in An Abandoned Fun House',2006,1,NULL,3,0.99,82,14.99,'R','Trailers,Behind the Scenes'),
('ALTER VICTORY','A Thoughtful Drama of a Composer And a Feminist who must Meet a Secret Agent in The Canadian Rockies',2006,1,NULL,6,0.99,57,27.99,'PG-13','Trailers,Behind the Scenes'),
('AMADEUS HOLY','A Emotional Display of a Pioneer And a Technical Writer who must Battle a Man in A Baloon Factory',2006,1,NULL,6,0.99,113,20.99,'PG','Commentaries,Deleted Scenes,Behind the Scenes'),
('AMELIE HELLFIGHTERS','A Boring Drama of a Woman And a Squirrel who must Conquer a Student in A Baloon Factory',2006,1,NULL,4,4.99,79,23.99,'R','Commentaries,Behind the Scenes'),
('AMERICAN CIRCUS','A Insightful Drama of a Girl And a Astronaut who must Face a Database Administrator in A Shark Tank',2006,1,NULL,3,4.99,129,17.99,'R','Commentaries,Behind the Scenes'),
('ANACONDA CONFESSIONS','A Lacklustur Display of a Dentist And a Dentist who must Fight a Girl in Australia',2006,1,NULL,3,0.99,92,9.99,'R','Trailers,Deleted Scenes'),
('ANALYZE HOOSIERS','A Thoughtful Display of a Explorer And a Pastry Chef who must Overcome a Feminist in The Sahara Desert',2006,1,NULL,6,2.99,181,28.99,'R','Trailers,Behind the Scenes'),
('ANGELS LIFE','A Thoughtful Display of a Woman And a Astronaut who must Battle a Robot in Berlin',2006,1,NULL,3,2.99,74,15.99,'G','Trailers'),
('ANNIE IDENTITY','A Amazing Panorama of a Pastry Chef And a Boat who must Escape a Woman in An Abandoned Amusement Park',2006,1,NULL,3,0.99,86,15.99,'G','Commentaries,Deleted Scenes'),
('ANONYMOUS HUMAN','A Amazing Reflection of a Database Administrator And a Astronaut who must Outrace a Database Administrator in A Shark Tank',2006,1,NULL,7,0.99,179,12.99,'NC-17','Deleted Scenes,Behind the Scenes'),
('MONSOON MUMBAI','A Emotional Saga of a Dancer And a Teacher who must Find Love in India',2018,10,1,5,3.99,145,24.99,'PG-13','Trailers,Behind the Scenes'),
('TOKYO DRIFT','A Fast-Paced Action of a Driver And a Mechanic who must Race in Tokyo',2015,3,1,4,4.99,130,19.99,'PG-13','Trailers,Deleted Scenes'),
('PARIS ROMANCE','A Touching Drama of a Writer And a Painter who must Find Love in Paris',2019,5,1,5,2.99,118,22.99,'PG','Commentaries,Behind the Scenes'),
('BERLIN WALL','A Thoughtful Documentary of a Spy And a Journalist who must Escape Berlin',2020,6,1,6,3.99,155,27.99,'R','Trailers,Commentaries,Deleted Scenes'),
('SEOUL SEARCH','A Action-Packed Thriller of a Detective And a Hacker who must Solve a Mystery in Seoul',2021,8,1,4,4.99,125,21.99,'PG-13','Trailers'),
('MOSCOW NIGHTS','A Epic Drama of a Composer And a Ballerina who must Overcome Adversity in Moscow',2017,11,1,7,2.99,160,29.99,'R','Commentaries,Deleted Scenes,Behind the Scenes'),
('MADRID MYSTERY','A Intrepid Thriller of a Detective And a Thief who must Chase a Criminal in Spain',2022,7,1,5,4.99,140,23.99,'PG-13','Trailers,Deleted Scenes'),
('SAO PAULO SUNSET','A Emotional Drama of a Musician And a Dancer who must Find Purpose in Brazil',2020,9,1,6,3.99,135,20.99,'PG','Behind the Scenes'),
('ROME HOLIDAY','A Charming Comedy of a Tourist And a Local who must Navigate Culture in Rome',2018,2,1,4,2.99,110,18.99,'G','Trailers,Commentaries'),
('SHANGHAI EXPRESS','A Fast-Paced Adventure of a Smuggler And a Detective who must Cross China',2021,4,1,5,4.99,150,26.99,'PG-13','Trailers,Deleted Scenes,Behind the Scenes'),
('QUANTUM PARADOX','A Mind-Bending Sci-Fi of a Physicist And a AI who must Save Humanity in The Future',2023,1,NULL,4,4.99,148,29.99,'PG-13','Trailers,Commentaries,Behind the Scenes'),
('DIGITAL FORTRESS','A Thrilling Saga of a Hacker And a Spy who must Decode a Secret in Silicon Valley',2023,1,NULL,5,3.99,132,24.99,'R','Trailers,Deleted Scenes'),
('OCEAN DEPTHS','A Breathtaking Documentary of Marine Life And Coral Reefs in The Pacific Ocean',2022,1,NULL,6,2.99,95,19.99,'G','Commentaries,Behind the Scenes'),
('MOUNTAIN ECHO','A Inspiring Drama of a Climber And a Guide who must Conquer Everest',2022,1,NULL,5,3.99,142,27.99,'PG','Trailers,Behind the Scenes'),
('CYBER REVOLT','A Action-Packed Thriller of a Robot And a Human who must Fight for Freedom in 2084',2024,1,NULL,3,4.99,115,22.99,'R','Trailers,Deleted Scenes,Behind the Scenes'),
('DESERT BLOOM','A Touching Story of a Botanist And a Nomad who must Find an Oasis in The Sahara',2021,1,NULL,6,2.99,128,20.99,'PG','Commentaries'),
('AURORA DREAMS','A Stunning Visual Journey Through the Northern Lights in Scandinavia',2023,1,NULL,5,3.99,88,25.99,'G','Trailers,Commentaries,Behind the Scenes'),
('PHANTOM CODE','A Suspenseful Thriller of a Programmer And a Spy who must Crack a Code in London',2024,1,NULL,4,4.99,138,23.99,'PG-13','Trailers,Deleted Scenes'),
('GRAVITY FALLS','A Emotional Coming-of-Age Story of Twins who must Solve Mysteries in Oregon',2020,1,NULL,6,2.99,105,18.99,'PG','Commentaries,Behind the Scenes'),
('SILENT WITNESS','A Gripping Legal Drama of a Lawyer And a Witness who must Find Justice in Chicago',2023,1,NULL,5,3.99,152,26.99,'R','Trailers,Commentaries,Deleted Scenes'),
('NEON HIGHWAY','A Stylish Thriller of a Driver And a Criminal who must Escape Through Las Vegas',2024,1,NULL,3,4.99,98,21.99,'R','Trailers,Behind the Scenes'),
('CORAL REEF','A Beautiful Documentary of Ocean Ecosystems And Conservation Efforts',2022,1,NULL,7,2.99,78,15.99,'G','Commentaries,Deleted Scenes'),
('MIDNIGHT SUN','A Romantic Drama of Two Strangers who must Find Love During an Arctic Summer',2021,1,NULL,5,3.99,120,22.99,'PG-13','Trailers,Behind the Scenes'),
('THUNDER ROAD','A Action-Packed Western of a Sheriff And a Bandit who must Face Off in The Desert',2023,1,NULL,4,4.99,135,24.99,'PG-13','Trailers,Deleted Scenes,Behind the Scenes'),
('ECHO CHAMBER','A Thought-Provoking Satire of Media And Politics in The Modern Age',2024,1,NULL,5,3.99,112,20.99,'R','Commentaries'),
('WINTER PALACE','A Epic Historical Drama of a Tsar And a Revolution in Saint Petersburg',2022,11,1,7,4.99,175,31.99,'R','Trailers,Commentaries,Deleted Scenes,Behind the Scenes'),
('JADE DRAGON','A Stunning Martial Arts Epic of a Warrior And a Master in Ancient China',2021,4,1,5,3.99,140,25.99,'PG-13','Trailers,Deleted Scenes'),
('SAHARA WIND','A Breathtaking Adventure of a Pilot And a Navigator who must Cross the Desert',2023,1,NULL,4,2.99,118,19.99,'PG','Trailers,Behind the Scenes'),
('PIXEL PERFECT','A Charming Animation About a Digital Artist who must Save a Virtual World',2024,1,NULL,3,4.99,92,17.99,'G','Trailers,Commentaries,Behind the Scenes'),
('CRIMSON TIDE','A Tense Submarine Thriller of a Captain And a Lieutenant who must Make a Decision',2020,1,NULL,5,3.99,155,28.99,'R','Trailers,Deleted Scenes'),
('EMERALD CITY','A Magical Fantasy of a Girl And a Wizard who must Save a Kingdom',2023,1,NULL,6,2.99,130,23.99,'PG','Trailers,Commentaries,Behind the Scenes'),
('SOLAR FLARE','A Sci-Fi Disaster Film of Astronauts who must Save Earth from a Solar Storm',2024,1,NULL,4,4.99,142,26.99,'PG-13','Trailers,Deleted Scenes'),
('VELVET UNDERGROUND','A Artistic Documentary of the Music Scene in 1960s New York',2021,1,NULL,5,3.99,98,22.99,'R','Commentaries,Behind the Scenes'),
('CRYSTAL CAVE','A Adventure Film of Explorers who must Discover a Hidden World Underground',2022,1,NULL,6,2.99,108,20.99,'PG','Trailers,Deleted Scenes'),
('ROCKET SCIENCE','A Comedy-Drama of a Stuttering Teen who must Win a Debate Competition',2020,1,NULL,3,0.99,85,14.99,'PG-13','Commentaries,Behind the Scenes'),
('AMBER ALERT','A Suspenseful Thriller of Parents who must Find Their Missing Child',2023,1,NULL,4,4.99,145,27.99,'R','Trailers,Deleted Scenes,Behind the Scenes'),
('COSMOS JOURNEY','A Awe-Inspiring Documentary of Space Exploration And the Universe',2024,1,NULL,7,3.99,165,32.99,'G','Trailers,Commentaries,Deleted Scenes,Behind the Scenes'),
('IRONCLAD BATTLE','A Epic War Film of Knights who must Defend a Castle in Medieval England',2022,1,NULL,5,4.99,158,29.99,'R','Trailers,Behind the Scenes'),
('SAPPHIRE SEA','A Romantic Adventure of a Sailor And a Marine Biologist in The Caribbean',2023,1,NULL,4,3.99,125,21.99,'PG','Trailers,Commentaries'),
('NEBULA RISING','A Sci-Fi Epic of a Space Captain who must Unite Alien Races Against a Common Foe',2024,1,NULL,5,4.99,168,30.99,'PG-13','Trailers,Commentaries,Behind the Scenes'),
('BAMBOO FOREST','A Meditative Drama Set in Rural Japan About a Potter Seeking Perfection',2021,3,1,6,2.99,115,21.99,'PG','Commentaries,Behind the Scenes');

-- ============================================================
-- 11. FILM_ACTOR (many-to-many ~400 rows)
-- ============================================================
CREATE TABLE film_actor (
  actor_id     SMALLINT UNSIGNED NOT NULL,
  film_id      SMALLINT UNSIGNED NOT NULL,
  last_update  TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (actor_id, film_id),
  FOREIGN KEY (actor_id) REFERENCES actor(actor_id) ON UPDATE CASCADE,
  FOREIGN KEY (film_id)  REFERENCES film(film_id)  ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

INSERT INTO film_actor (actor_id, film_id) VALUES
-- 5 actors per film on average
(1,1),(2,1),(3,1),(4,1),(5,1),
(6,2),(7,2),(8,2),(9,2),(10,2),
(11,3),(12,3),(13,3),(14,3),(15,3),
(16,4),(17,4),(18,4),(19,4),(20,4),
(21,5),(22,5),(23,5),(24,5),(25,5),
(26,6),(27,6),(28,6),(29,6),(30,6),
(31,7),(32,7),(33,7),(34,7),(35,7),
(36,8),(37,8),(38,8),(39,8),(40,8),
(41,9),(42,9),(43,9),(44,9),(45,9),
(46,10),(47,10),(48,10),(49,10),(50,10),
(51,11),(52,11),(53,11),(54,11),(55,11),
(56,12),(57,12),(58,12),(59,12),(60,12),
(61,13),(62,13),(63,13),(64,13),(65,13),
(66,14),(67,14),(68,14),(69,14),(70,14),
(71,15),(72,15),(73,15),(74,15),(75,15),
(76,16),(77,16),(78,16),(79,16),(80,16),
(81,17),(82,17),(83,17),(84,17),(85,17),
(86,18),(87,18),(88,18),(89,18),(90,18),
(91,19),(92,19),(93,19),(94,19),(95,19),
(96,20),(97,20),(98,20),(99,20),(100,20),
(101,21),(102,21),(103,21),(104,21),(105,21),
(106,22),(107,22),(108,22),(109,22),(110,22),
(111,23),(112,23),(113,23),(114,23),(115,23),
(116,24),(117,24),(118,24),(119,24),(120,24),
(121,25),(122,25),(123,25),(124,25),(125,25),
(126,26),(127,26),(128,26),(129,26),(130,26),
(131,27),(132,27),(133,27),(134,27),(135,27),
(136,28),(137,28),(138,28),(139,28),(140,28),
(141,29),(142,29),(143,29),(144,29),(145,29),
(146,30),(147,30),(148,30),(149,30),(150,30),
(151,31),(152,31),(153,31),(154,31),(155,31),
(156,32),(157,32),(158,32),(159,32),(160,32),
(1,33),(2,33),(3,33),(4,33),(5,33),
(6,34),(7,34),(8,34),(9,34),(10,34),
(11,35),(12,35),(13,35),(14,35),(15,35),
(16,36),(17,36),(18,36),(19,36),(20,36),
(21,37),(22,37),(23,37),(24,37),(25,37),
(26,38),(27,38),(28,38),(29,38),(30,38),
(31,39),(32,39),(33,39),(34,39),(35,39),
(36,40),(37,40),(38,40),(39,40),(40,40),
(41,41),(42,41),(43,41),(44,41),(45,41),
(46,42),(47,42),(48,42),(49,42),(50,42),
(51,43),(52,43),(53,43),(54,43),(55,43),
(56,44),(57,44),(58,44),(59,44),(60,44),
(61,45),(62,45),(63,45),(64,45),(65,45),
(66,46),(67,46),(68,46),(69,46),(70,46),
(71,47),(72,47),(73,47),(74,47),(75,47),
(76,48),(77,48),(78,48),(79,48),(80,48),
(81,49),(82,49),(83,49),(84,49),(85,49),
(86,50),(87,50),(88,50),(89,50),(90,50),
(91,51),(92,51),(93,51),(94,51),(95,51),
(96,52),(97,52),(98,52),(99,52),(100,52),
(101,53),(102,53),(103,53),(104,53),(105,53),
(106,54),(107,54),(108,54),(109,54),(110,54),
(111,55),(112,55),(113,55),(114,55),(115,55),
(116,56),(117,56),(118,56),(119,56),(120,56),
(121,57),(122,57),(123,57),(124,57),(125,57),
(126,58),(127,58),(128,58),(129,58),(130,58),
(131,59),(132,59),(133,59),(134,59),(135,59),
(136,60),(137,60),(138,60),(139,60),(140,60),
(141,61),(142,61),(143,61),(144,61),(145,61),
(146,62),(147,62),(148,62),(149,62),(150,62),
(151,63),(152,63),(153,63),(154,63),(155,63),
(156,64),(157,64),(158,64),(159,64),(160,64),
(1,65),(2,65),(3,65),(4,65),(5,65);

-- ============================================================
-- 12. FILM_CATEGORY (many-to-many)
-- ============================================================
CREATE TABLE film_category (
  film_id      SMALLINT UNSIGNED NOT NULL,
  category_id  TINYINT UNSIGNED NOT NULL,
  last_update  TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (film_id, category_id),
  FOREIGN KEY (film_id)     REFERENCES film(film_id)         ON UPDATE CASCADE,
  FOREIGN KEY (category_id) REFERENCES category(category_id) ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

INSERT INTO film_category (film_id, category_id) VALUES
(1,6),(2,11),(3,6),(4,11),(5,8),(6,9),(7,5),(8,11),(9,11),(10,15),
(11,9),(12,15),(13,7),(14,14),(15,9),(16,2),(17,4),(18,11),(19,6),(20,7),
(21,1),(22,14),(23,3),(24,3),(25,14),
(26,7),(27,1),(28,7),(29,6),(30,1),(31,7),(32,1),(33,5),(34,7),(35,1),
(36,14),(37,1),(38,6),(39,7),(40,1),(41,6),(42,14),(43,7),(44,1),(45,7),
(46,1),(47,11),(48,9),(49,7),(50,14),
(51,5),(52,3),(53,15),(54,16),(55,12),(56,14),(57,1),(58,7),(59,5),(60,11),
(61,6),(62,8),(63,14),(64,15),(65,7);

-- ============================================================
-- 13. INVENTORY (~460 items via INSERT SELECT)
-- ============================================================
CREATE TABLE inventory (
  inventory_id MEDIUMINT UNSIGNED NOT NULL AUTO_INCREMENT,
  film_id      SMALLINT UNSIGNED NOT NULL,
  store_id     TINYINT UNSIGNED NOT NULL,
  last_update  TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (inventory_id),
  FOREIGN KEY (film_id)  REFERENCES film(film_id)   ON UPDATE CASCADE,
  FOREIGN KEY (store_id) REFERENCES store(store_id)  ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- Each film gets 4 copies spread across stores
INSERT INTO inventory (film_id, store_id)
SELECT f.film_id, s.store_id
FROM film f
CROSS JOIN store s
CROSS JOIN (SELECT 1 AS n UNION ALL SELECT 2 UNION ALL SELECT 3 UNION ALL SELECT 4) copies
WHERE (f.film_id BETWEEN 1 AND 13 AND s.store_id = 1)
   OR (f.film_id BETWEEN 14 AND 25 AND s.store_id = 2)
   OR (f.film_id BETWEEN 26 AND 40 AND s.store_id = 3)
   OR (f.film_id BETWEEN 41 AND 55 AND s.store_id = 4)
   OR (f.film_id BETWEEN 56 AND 65 AND s.store_id = 5);

-- Extra copies in neighbouring stores for popular films
INSERT INTO inventory (film_id, store_id)
SELECT f.film_id, IF(s.store_id < 5, s.store_id + 1, 1) AS alt_store
FROM film f
CROSS JOIN store s
WHERE f.film_id IN (1,5,10,15,20,26,30,36,42,48,55,60,65)
  AND s.store_id IN (1,3,5);

-- ============================================================
-- 14. RENTAL (~1800 rows via INSERT SELECT)
-- ============================================================
CREATE TABLE rental (
  rental_id    INT NOT NULL AUTO_INCREMENT,
  rental_date  DATETIME NOT NULL,
  inventory_id MEDIUMINT UNSIGNED NOT NULL,
  customer_id  SMALLINT UNSIGNED NOT NULL,
  return_date  DATETIME DEFAULT NULL,
  staff_id     TINYINT UNSIGNED NOT NULL,
  last_update  TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (rental_id),
  FOREIGN KEY (inventory_id) REFERENCES inventory(inventory_id) ON UPDATE CASCADE,
  FOREIGN KEY (customer_id)  REFERENCES customer(customer_id)   ON UPDATE CASCADE,
  FOREIGN KEY (staff_id)     REFERENCES staff(staff_id)         ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- ~1750 rentals spread across 2023-2024 using deterministic arithmetic
INSERT INTO rental (rental_date, inventory_id, customer_id, return_date, staff_id)
SELECT
  DATE_ADD('2023-01-01', INTERVAL (seq.n * 11 + inv.inventory_id * 3) % 700 DAY) AS rental_date,
  inv.inventory_id,
  1 + (seq.n * 7 + inv.inventory_id * 13) % 150 AS customer_id,
  DATE_ADD(
    DATE_ADD('2023-01-01', INTERVAL (seq.n * 11 + inv.inventory_id * 3) % 700 DAY),
    INTERVAL 1 + (seq.n % 14) DAY
  ) AS return_date,
  1 + (seq.n + inv.inventory_id) % 10 AS staff_id
FROM inventory inv
CROSS JOIN (
  SELECT 1 AS n UNION ALL SELECT 2 UNION ALL SELECT 3 UNION ALL SELECT 4
  UNION ALL SELECT 5 UNION ALL SELECT 6 UNION ALL SELECT 7
) seq
WHERE inv.inventory_id <= 250;

-- ~50 unreturned (still outstanding) rentals
INSERT INTO rental (rental_date, inventory_id, customer_id, return_date, staff_id)
SELECT
  DATE_ADD('2024-11-15', INTERVAL inv.inventory_id % 30 DAY) AS rental_date,
  inv.inventory_id,
  1 + inv.inventory_id % 100 AS customer_id,
  NULL AS return_date,
  1 + inv.inventory_id % 10 AS staff_id
FROM inventory inv
WHERE inv.inventory_id > 250 AND inv.inventory_id <= 300;

-- ============================================================
-- 15. PAYMENT (~1500 rows via INSERT SELECT)
-- ============================================================
CREATE TABLE payment (
  payment_id   SMALLINT UNSIGNED NOT NULL AUTO_INCREMENT,
  customer_id  SMALLINT UNSIGNED NOT NULL,
  staff_id     TINYINT UNSIGNED NOT NULL,
  rental_id    INT DEFAULT NULL,
  amount       DECIMAL(5,2) NOT NULL,
  payment_date DATETIME NOT NULL,
  last_update  TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (payment_id),
  FOREIGN KEY (customer_id) REFERENCES customer(customer_id) ON UPDATE CASCADE,
  FOREIGN KEY (staff_id)    REFERENCES staff(staff_id)       ON UPDATE CASCADE,
  FOREIGN KEY (rental_id)   REFERENCES rental(rental_id)     ON UPDATE CASCADE ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- One payment per rental (with slight amount variation)
INSERT INTO payment (customer_id, staff_id, rental_id, amount, payment_date)
SELECT
  r.customer_id,
  r.staff_id,
  r.rental_id,
  f.rental_rate + ROUND((r.rental_id % 5) * 0.50, 2) AS amount,
  DATE_ADD(r.rental_date, INTERVAL 1 HOUR) AS payment_date
FROM rental r
JOIN inventory inv ON r.inventory_id = inv.inventory_id
JOIN film f ON inv.film_id = f.film_id
WHERE r.return_date IS NOT NULL
  AND r.rental_id <= 1500;

-- ============================================================
-- 16. FILM_TEXT (full-text search)
-- ============================================================
CREATE TABLE film_text (
  film_id     SMALLINT NOT NULL,
  title       VARCHAR(255) NOT NULL,
  description TEXT,
  PRIMARY KEY (film_id),
  FULLTEXT KEY idx_title_description (title, description)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

INSERT INTO film_text (film_id, title, description)
SELECT film_id, title, description FROM film;

-- ============================================================
-- ANALYTICS VIEWS
-- ============================================================

-- View: customer rental summary
CREATE OR REPLACE VIEW customer_rental_summary AS
SELECT
  c.customer_id,
  CONCAT(c.first_name, ' ', c.last_name) AS customer_name,
  c.email,
  co.country,
  ci.city,
  COUNT(r.rental_id) AS total_rentals,
  COALESCE(SUM(p.amount), 0) AS total_payments,
  MAX(r.rental_date) AS last_rental_date
FROM customer c
JOIN address a ON c.address_id = a.address_id
JOIN city ci ON a.city_id = ci.city_id
JOIN country co ON ci.country_id = co.country_id
LEFT JOIN rental r ON c.customer_id = r.customer_id
LEFT JOIN payment p ON r.rental_id = p.rental_id
GROUP BY c.customer_id, customer_name, c.email, co.country, ci.city;

-- View: film rental stats
CREATE OR REPLACE VIEW film_rental_stats AS
SELECT
  f.film_id,
  f.title,
  c.name AS category,
  l.name AS language,
  f.rating,
  f.rental_rate,
  f.length,
  COUNT(r.rental_id) AS times_rented,
  COALESCE(SUM(p.amount), 0) AS total_revenue
FROM film f
JOIN language l ON f.language_id = l.language_id
LEFT JOIN film_category fc ON f.film_id = fc.film_id
LEFT JOIN category c ON fc.category_id = c.category_id
LEFT JOIN inventory inv ON f.film_id = inv.film_id
LEFT JOIN rental r ON inv.inventory_id = r.inventory_id
LEFT JOIN payment p ON r.rental_id = p.rental_id
GROUP BY f.film_id, f.title, c.name, l.name, f.rating, f.rental_rate, f.length;

-- Done! Schema summary:
-- 16 tables: country, city, address, store, staff, customer,
--            language, category, actor, film, film_actor,
--            film_category, inventory, rental, payment, film_text
-- 2 views:   customer_rental_summary, film_rental_stats
-- ~65 countries, ~90 cities, ~90 addresses, 5 stores, 10 staff,
--   150 customers, 15 languages, 16 categories, 160 actors,
--   65 films, ~325 film_actor, ~65 film_category,
--   ~460 inventory, ~1800 rentals, ~1500 payments
-- Total: ~4500+ rows across all tables
