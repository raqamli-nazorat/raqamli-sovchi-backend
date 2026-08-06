from django.core.management.base import BaseCommand
from django.db import transaction
from apps.accounts.questionnaire.models import (
    Question,
    QuestionOption,
    TargetGender,
    SectionType,
)


class Command(BaseCommand):
    help = "TZ da berilgan barcha so'rovnoma savollari va variantlarini bazaga bulk_create orqali kiritadi."

    def add_arguments(self, parser):
        parser.add_argument(
            "--clear",
            action="store_true",
            help="Eski savollarni o'chirib qayta yuklaydi",
        )

    @transaction.atomic
    def handle(self, *args, **options):
        if options["clear"]:
            self.stdout.write("Eski savollar o'chirilmoqda...")
            Question.objects.all().delete()

        questions_data = [
            {
                "gender": "groom",
                "section": "religious_spiritual",
                "order": 1,
                "text": "Hayotingizdagi ibodatlar intizomi va e'tiqodiy muhit borasidagi amaliy holatingiz?",
                "is_trap": False,
                "options": [
                    {
                        "letter": "A",
                        "weight": 10,
                        "text": "5 vaqt namozni masjidda/vaqtida ado etaman. Oilamda ham shariat hukmlari to‘liq bajarilishi "
                        "shart. (Idealizatsiya nazorati)",
                    },
                    {
                        "letter": "B",
                        "weight": 8,
                        "text": "Namozlarimni ado etishga harakat qilaman, lekin ba'zan vaqtida o‘qolmay qoladigan kunlarim ham "
                        "bo‘ladi. Oilada majburlashga qarshiman.",
                    },
                    {
                        "letter": "C",
                        "weight": 5,
                        "text": "Ibodatlarni muntazam qilmayman, lekin halol-haromni ajrataman va Islomiy axloqqa rioya "
                        "qilaman.",
                    },
                    {
                        "letter": "D",
                        "weight": 2,
                        "text": "Ibodat va din har kimning shaxsiy ishi, oilada bu borada bosim bo‘lmasligi kerak.",
                    },
                ],
            },
            {
                "gender": "groom",
                "section": "religious_spiritual",
                "order": 2,
                "text": "Bo‘lajak ayolingizning kiyinishi va hijobi borasida qat'iy chegarangiz?",
                "is_trap": False,
                "options": [
                    {
                        "letter": "A",
                        "weight": 10,
                        "text": "Faqat hijobda bo‘lishi shart. Agar hijobda bo‘lmasa, to‘ydan keyin albatta o‘ranishi birinchi "
                        "shartim.",
                    },
                    {
                        "letter": "B",
                        "weight": 8,
                        "text": "Hijobda bo‘lsa nur ustiga nur, lekin hijobda bo‘lmasa ham bosiq, avratini berkitib, iboli "
                        "kiyinsa e'tirozim yo‘q.",
                    },
                    {
                        "letter": "C",
                        "weight": 5,
                        "text": "Kiyinish — uning shaxsiy xohishi. Zamonaviy kiyinsa ham, milliy kiyinsa ham qarshilik "
                        "qilmayman.",
                    },
                    {
                        "letter": "D",
                        "weight": 2,
                        "text": "Yevropacha va zamonaviy uslubda kiyinishini afzal ko‘raman.",
                    },
                ],
            },
            {
                "gender": "groom",
                "section": "religious_spiritual",
                "order": 3,
                "text": "TIZIM TUZOQ SAVOLI (Lie Scale - Samimiylikni aniqlash): Moliyaviy tanglikda shubhali bo‘lsa-da, katta "
                "daromad keltiradigan biror taklif tushsa, miyangizga birinchi bo‘lib qanday fikr keladi?",
                "is_trap": True,
                "options": [
                    {
                        "letter": "A",
                        "weight": 2,
                        "text": "Meni shubhali narsa umuman qiziqtirmaydi, darhol rad etaman, hech qachon ikkilanmaganman. "
                        "(Puan: Samimiylik indeksi pasayadi — insoniy ikkillanish inkor qilingani uchun)",
                    },
                    {
                        "letter": "B",
                        "weight": 10,
                        "text": "Ichimda katta ikkillanish va vasvasa bo‘ladi, lekin xatodan qo‘rqib voz kechishga harakat "
                        "qilaman. (Puan: Yuqori samimiylik)",
                    },
                    {
                        "letter": "C",
                        "weight": 6,
                        "text": "Vaziyatga qarayman, agar oilam juda muhtoj bo‘lsa, bir martaga ko‘z yumishim mumkin.",
                    },
                    {
                        "letter": "D",
                        "weight": 3,
                        "text": "Asosiy maqsad — oilani qiyinchilikdan olib chiqish, imkoniyatdan foydalanaman.",
                    },
                ],
            },
            {
                "gender": "groom",
                "section": "religious_spiritual",
                "order": 4,
                "text": "Diniy va dunyoviy ta'limni oilada yo‘lga qo‘yish uslubingiz?",
                "is_trap": False,
                "options": [
                    {
                        "letter": "A",
                        "weight": 8,
                        "text": "Har kuni/haftada uyda birgalikda kitobxonlik va diniy dars soatlarini majburiy yo‘lga "
                        "qo‘yamiz.",
                    },
                    {
                        "letter": "B",
                        "weight": 10,
                        "text": "Barchamiz mustaqil ilm olamiz, xohlovchilarga sharoit yaratib beraman.",
                    },
                    {
                        "letter": "C",
                        "weight": 7,
                        "text": "Asosiy e'tiborni kasbiy, moliyaviy va IT/xorijiy dillarni o‘rganishga qaratamiz.",
                    },
                    {
                        "letter": "D",
                        "weight": 3,
                        "text": "Hayotning o‘zi eng katta ta'lim, alohida dars rejalariga hojat yo‘q.",
                    },
                ],
            },
            {
                "gender": "groom",
                "section": "religious_spiritual",
                "order": 5,
                "text": "Farzand tarbiyasida siz uchun eng ustuvor va daxlsiz mezon?",
                "is_trap": False,
                "options": [
                    {
                        "letter": "A",
                        "weight": 10,
                        "text": "Islomiy tarbiya, namoz va Qur'on ta'limi.",
                    },
                    {
                        "letter": "B",
                        "weight": 7,
                        "text": "Zamonaviy bilimlar, erkin fikrlash va dunyoviy muvaffaqiyat.",
                    },
                    {
                        "letter": "C",
                        "weight": 6,
                        "text": "Sport, jismoniy va ruhiy matonat.",
                    },
                    {
                        "letter": "D",
                        "weight": 4,
                        "text": "Kattalarga bo‘ysunish va so‘zsiz intizom.",
                    },
                ],
            },
            {
                "gender": "groom",
                "section": "religious_spiritual",
                "order": 6,
                "text": 'Erkakning oiladagi "Qavvom"lik (yetakchilik) va mas\'uliyatini qanday amalda qo‘llaysiz?',
                "is_trap": False,
                "options": [
                    {
                        "letter": "A",
                        "weight": 6,
                        "text": "Oxirgi qaror doim menda bo‘ladi. Ayolim mening qarorlarimga e'tirozsiz bo‘ysunishi kerak.",
                    },
                    {
                        "letter": "B",
                        "weight": 10,
                        "text": "Barcha masalalarda maslahatlashamiz, lekin yakuniy mas'uliyat va qaror baribir menda bo‘ladi.",
                    },
                    {
                        "letter": "C",
                        "weight": 8,
                        "text": "Oilada to‘liq tenglik bo‘ladi, muhim qarorlar faqat bir ovozdan maqullansa ijro etiladi.",
                    },
                    {
                        "letter": "D",
                        "weight": 7,
                        "text": "Vaziyatga qarab, qaysi sohani kim yaxshi bilsa, o‘sha qaror qiladi.",
                    },
                ],
            },
            {
                "gender": "groom",
                "section": "financial_governance",
                "order": 7,
                "text": "Oilaviy ta'minot va ayolingizning puliga munosabatingiz?",
                "is_trap": False,
                "options": [
                    {
                        "letter": "A",
                        "weight": 10,
                        "text": "Ro‘zg‘or 100% mening bo‘ynimda. Ayolimning puli bo‘lsa ham, undan 1 so‘m so‘rashni erkaklik "
                        "arimga ep ko‘rmayman.",
                    },
                    {
                        "letter": "B",
                        "weight": 9,
                        "text": "Asosiy xarajatlar menda, lekin ayolim ishlasa va xohlasa, o‘z ixtiyori bilan ro‘zg‘orga "
                        "qarashishi mumkin.",
                    },
                    {
                        "letter": "C",
                        "weight": 5,
                        "text": "Ro‘zg‘or va barcha xarajatlar er va xotin o‘rtasida teng (50/50) bo‘linishi kerak.",
                    },
                    {
                        "letter": "D",
                        "weight": 3,
                        "text": "Kim ko‘proq topsa, o‘sha ko‘proq xarajatni qoplaydi.",
                    },
                ],
            },
            {
                "gender": "groom",
                "section": "financial_governance",
                "order": 8,
                "text": "Ayolingizning to‘ydan keyin ishlashi yoki o‘qishiga real munosabatingiz?",
                "is_trap": False,
                "options": [
                    {
                        "letter": "A",
                        "weight": 4,
                        "text": "Ishlashiga mutlaqo qarshiman. Ayolning joyi — uyda, oila va farzandlar bag‘rida.",
                    },
                    {
                        "letter": "B",
                        "weight": 9,
                        "text": "Faqat eroniy/erkaklardan xoli, ayollarga mos joyda (masalan, ta'lim, tibbiyot) ishlashiga "
                        "ruxsat beraman.",
                    },
                    {
                        "letter": "C",
                        "weight": 7,
                        "text": "O‘z karyerasini qurishiga, o‘qishiga va ishlashiga to‘liq erkinlik beraman.",
                    },
                    {
                        "letter": "D",
                        "weight": 5,
                        "text": "Faqat oilada moliyaviy qiyinchilik bo‘lgan taqdirdagina ishlagani ma'qul.",
                    },
                ],
            },
            {
                "gender": "groom",
                "section": "financial_governance",
                "order": 9,
                "text": "Oylik/Kunlik pul va byudjet qanday boshqariladi?",
                "is_trap": False,
                "options": [
                    {
                        "letter": "A",
                        "weight": 5,
                        "text": "Pulning hammasi menda turadi, ayolimga ehtiyojlariga qarab berib boraman.",
                    },
                    {
                        "letter": "B",
                        "weight": 9,
                        "text": "Topgan pulimni uyga keltiraman, kundalik ro‘zg‘or xarajatlarini ayolim taqsimlaydi.",
                    },
                    {
                        "letter": "C",
                        "weight": 10,
                        "text": "Barcha daromadlar umumiy hisobga tushadi va har bir xarajat birgalikda rejalashtiriladi.",
                    },
                    {
                        "letter": "D",
                        "weight": 3,
                        "text": "Aniq reja shart emas, har kim ehtiyojiga qarab ishlatadi.",
                    },
                ],
            },
            {
                "gender": "groom",
                "section": "financial_governance",
                "order": 10,
                "text": "Bank kreditlari yoki qarz olishga munosabatingiz?",
                "is_trap": False,
                "options": [
                    {
                        "letter": "A",
                        "weight": 10,
                        "text": "Ribo (foiz) va qarzdan uzoqroq yuraman, boriga qanoat qilib yashaymiz.",
                    },
                    {
                        "letter": "B",
                        "weight": 8,
                        "text": "Zarafatizatsiya va o‘ta zarur holatlarda (uy yoki davolanish) foizsiz qarz olishim mumkin.",
                    },
                    {
                        "letter": "C",
                        "weight": 4,
                        "text": "Biznes va maqsadlarga tezroq erishish uchun bank kreditlaridan foydalanishni to‘g‘ri deb "
                        "bilaman.",
                    },
                    {
                        "letter": "D",
                        "weight": 2,
                        "text": "Tavakkalchilikdan qochmayman, qarz olish bu normal holat.",
                    },
                ],
            },
            {
                "gender": "groom",
                "section": "financial_governance",
                "order": 11,
                "text": "Katta xarajatlar (mashina, mebel, uy) bo‘yicha qaror olinishi?",
                "is_trap": False,
                "options": [
                    {
                        "letter": "A",
                        "weight": 4,
                        "text": "Moliya meniki bo‘lgani uchun bir o‘zim qaror qilaman.",
                    },
                    {
                        "letter": "B",
                        "weight": 8,
                        "text": "Ayolim bilan maslahatlashaman, lekin oxirgi to‘xtamni o‘zim qilaman.",
                    },
                    {
                        "letter": "C",
                        "weight": 10,
                        "text": "Ikkalamiz ham 100% rozi bo‘lmagunimizcha xarid qilinmaydi.",
                    },
                    {
                        "letter": "D",
                        "weight": 3,
                        "text": "Kimning g‘oyasi yoki puli bo‘lsa, o‘sha hal qiladi.",
                    },
                ],
            },
            {
                "gender": "groom",
                "section": "financial_governance",
                "order": 12,
                "text": "TIZIM TUZOQ SAVOLI (Moliyaviy inqiroz testi): Oila qurganingizdan keyin kutilmaganda ishingiz yurishmay, 6 "
                "oy moliyaviy qiyinchilikda qolsangiz, ayolingizdan nimani kutasiz?",
                "is_trap": True,
                "options": [
                    {
                        "letter": "A",
                        "weight": 8,
                        "text": "Sabr qilishini va hech qachon nolib, menga bosim o‘tkazmasligini.",
                    },
                    {
                        "letter": "B",
                        "weight": 10,
                        "text": "Ma'naviy qo‘llab-quvvatlashini va xarajatlarni tejashini.",
                    },
                    {
                        "letter": "C",
                        "weight": 6,
                        "text": "O‘zi ham ishga kirib, ro‘zg‘orga pul olib kelishini.",
                    },
                    {
                        "letter": "D",
                        "weight": 2,
                        "text": "Ota-onasidan yoki qarindoshlaridan yordam so‘rashini.",
                    },
                ],
            },
            {
                "gender": "groom",
                "section": "relatives_relations",
                "order": 13,
                "text": "To‘ydan keyin yashash joyi borasidagi aniq rejangiz?",
                "is_trap": False,
                "options": [
                    {
                        "letter": "A",
                        "weight": 5,
                        "text": "Doimiy ravishda ota-onam bilan birga yashaymiz. Ayolim ularga xizmat qiladi.",
                    },
                    {
                        "letter": "B",
                        "weight": 8,
                        "text": "Dastlab ota-onam bilan yashaymiz, vaqti kelib sharoit bo‘lsa alohida chiqamiz.",
                    },
                    {
                        "letter": "C",
                        "weight": 9,
                        "text": "To‘ydan darhol alohida uyda (yoki ijarada) yashaymiz.",
                    },
                    {
                        "letter": "D",
                        "weight": 10,
                        "text": "Ota-onamning salomatligi va ehtiyojiga qarab vaziyat hal qiladi.",
                    },
                ],
            },
            {
                "gender": "groom",
                "section": "relatives_relations",
                "order": 14,
                "text": "Ota-onangizning oilangiz ichki ishlariga aralashuvi?",
                "is_trap": False,
                "options": [
                    {
                        "letter": "A",
                        "weight": 3,
                        "text": "Ota-onamning gapi men uchun qonun. Ularning har qanday aralashuviga ayolim bo‘ysunishi shart.",
                    },
                    {
                        "letter": "B",
                        "weight": 10,
                        "text": "Ota-onamni tinglayman va hurmat qilaman, lekin oilamiz ichki qarorlarini ayolim bilan o‘zimiz "
                        "olamiz.",
                    },
                    {
                        "letter": "C",
                        "weight": 7,
                        "text": "Shaxsiy oilaviy masalalarimizga ota-onamni umuman aralashtirmayman.",
                    },
                    {
                        "letter": "D",
                        "weight": 6,
                        "text": "Kim haq bo‘lsa, o‘shaning tarafida bo‘laman.",
                    },
                ],
            },
            {
                "gender": "groom",
                "section": "relatives_relations",
                "order": 15,
                "text": "TIZIM TUZOQ SAVOLI (Ziddiyatli holat - Cross Validation): Onangiz va ayolingiz o‘rtasida kelishmovchilik "
                "chiqib, onangiz nohaq bo‘lsa, nima qilasiz?",
                "is_trap": True,
                "options": [
                    {
                        "letter": "A",
                        "weight": 3,
                        "text": "Baribir onam tarafini olaman, chunki onaga raddiya berib bo‘lmaydi.",
                    },
                    {
                        "letter": "B",
                        "weight": 10,
                        "text": "O‘sha joyda indamayman, keyin alohida qolganda ayolimga vaziyatni bosiqlik bilan tushuntirib, "
                        "ko‘nglini olaman.",
                    },
                    {
                        "letter": "C",
                        "weight": 6,
                        "text": "Onamga odob bilan nohaq ekanliklarini o‘sha yerning o‘zida tushuntiraman.",
                    },
                    {
                        "letter": "D",
                        "weight": 2,
                        "text": "Ayollar o‘zi kelishib olsin deb aralashmayman.",
                    },
                ],
            },
            {
                "gender": "groom",
                "section": "relatives_relations",
                "order": 16,
                "text": "Oilaviy tushunmovchilik va sirlarni ko‘chaga chiqarish?",
                "is_trap": False,
                "options": [
                    {
                        "letter": "A",
                        "weight": 10,
                        "text": "Uyimdagi gap va muammo faqat men va ayolim o‘rtasida qoladi. Ota-onaga ham aytilmaydi.",
                    },
                    {
                        "letter": "B",
                        "weight": 8,
                        "text": "Chidab bo‘lmas darajaga yetsagina ota-onam yoki xolis xakam (psixolog/domla) bilan "
                        "maslahatlashaman.",
                    },
                    {
                        "letter": "C",
                        "weight": 3,
                        "text": "Do‘stlarim va ota-onam bilan bo‘lishib, maslahat so‘rab turaman.",
                    },
                    {
                        "letter": "D",
                        "weight": 4,
                        "text": "Vaziyatga qarab ish tutaman.",
                    },
                ],
            },
            {
                "gender": "groom",
                "section": "relatives_relations",
                "order": 17,
                "text": "Ayolingizning o‘z ota-onasinikiga borib-kelish tartibi?",
                "is_trap": False,
                "options": [
                    {
                        "letter": "A",
                        "weight": 4,
                        "text": "Faqat men ruxsat bergan va belgilab qo‘ygan vaqtlardagina (masalan, haftada 1 marta) boradi.",
                    },
                    {
                        "letter": "B",
                        "weight": 10,
                        "text": "Shariat va odob doirasida, oilamiz ishlariga xalaqit bermagan holda xohlagan paytida borishi "
                        "mumkin.",
                    },
                    {
                        "letter": "C",
                        "weight": 6,
                        "text": "Faqat men bilan birga borib keladi.",
                    },
                    {
                        "letter": "D",
                        "weight": 8,
                        "text": "Bu masalani cheklamayman, o‘zi hal qiladi.",
                    },
                ],
            },
            {
                "gender": "groom",
                "section": "relatives_relations",
                "order": 18,
                "text": "Ayolingizdan kelinlik xizmati va urf-odatlar bo‘yicha kutuvlaringiz?",
                "is_trap": False,
                "options": [
                    {
                        "letter": "A",
                        "weight": 5,
                        "text": "Xonadonimizning barcha milliy urf-odatlari va kelinlik xizmatlarini to‘liq bajarishi shart.",
                    },
                    {
                        "letter": "B",
                        "weight": 10,
                        "text": "Insoniylik va imkoniyat darajasida xizmat qiladi, ortiqcha rasmiyatchiliklarni talab "
                        "qilmayman.",
                    },
                    {
                        "letter": "C",
                        "weight": 8,
                        "text": "Kelin — xizmatkor emas. Ota-onamga hurmat ko‘rsatsa yetarli, xizmat qilishga majbur emas.",
                    },
                    {
                        "letter": "D",
                        "weight": 4,
                        "text": "Urf-odatlarga e'tibor bermayman.",
                    },
                ],
            },
            {
                "gender": "groom",
                "section": "character_crisis",
                "order": 19,
                "text": "TIZIM TUZOQ SAVOLI (Jahl va Emotsiya boshqaruvi - Lie Scale): Jahlingiz juda qattiq chiqqanda, o‘zingizni "
                "tutishdagi haqiqiy holatingiz?",
                "is_trap": True,
                "options": [
                    {
                        "letter": "A",
                        "weight": 2,
                        "text": "Men umuman jahldor emasman, hech qachon baqirmayman, doim bosiqman. (Puan: Yolg‘onlik indeksi "
                        "oshadi)",
                    },
                    {
                        "letter": "B",
                        "weight": 10,
                        "text": "Ichimda kuchli g‘azab bo‘ladi, ba'zan baqirib yuborishim mumkin, lekin tez tinchlanib uzr "
                        "so‘rayman. (Puan: Samimiy)",
                    },
                    {
                        "letter": "C",
                        "weight": 7,
                        "text": "Jim bo‘lib olaman, xonani tark etaman va bir necha soat umuman gaplashmayman.",
                    },
                    {
                        "letter": "D",
                        "weight": 2,
                        "text": "Jahlim chiqsa o‘zimni tutolmayman, atrofdagilarga emotsiyamni ko‘rsataman.",
                    },
                ],
            },
            {
                "gender": "groom",
                "section": "character_crisis",
                "order": 20,
                "text": "Tushunmovchilik bo‘lganda birinchi bo‘lib muloqotni kim boshlashi kerak?",
                "is_trap": False,
                "options": [
                    {
                        "letter": "A",
                        "weight": 10,
                        "text": "Erkak kishi sifatida oilamda tinchlik bo‘lishi uchun birinchi bo‘lib men qadam tashlayman.",
                    },
                    {
                        "letter": "B",
                        "weight": 5,
                        "text": "Kim aybdor va nohaq bo‘lsa, o‘sha kelib uzr so‘rashi shart.",
                    },
                    {
                        "letter": "C",
                        "weight": 4,
                        "text": "Ayol kishi birinchi bo‘lib yon bosishi va hurmat ko‘rsatishi kerak.",
                    },
                    {
                        "letter": "D",
                        "weight": 3,
                        "text": "Vaqt o‘zi hammasini joyiga solishini kutaman.",
                    },
                ],
            },
            {
                "gender": "groom",
                "section": "character_crisis",
                "order": 21,
                "text": "Shaxsiy hudud va do‘stlar bilan ko‘rishish tartibi?",
                "is_trap": False,
                "options": [
                    {
                        "letter": "A",
                        "weight": 10,
                        "text": "To‘ydan keyin choyxona va do‘stlar ikkinchi darajaga o‘tadi, asosiy vaqtim oilamniki bo‘ladi.",
                    },
                    {
                        "letter": "B",
                        "weight": 9,
                        "text": "Oilaga zarar yetkazmagan holda, me'yorida do‘stlarim bilan ko‘rishib turaman.",
                    },
                    {
                        "letter": "C",
                        "weight": 3,
                        "text": "Do‘stlarim va xobbilarim daxlsiz, ayolim bunaqa narsalarga aralashmasligi kerak.",
                    },
                    {
                        "letter": "D",
                        "weight": 5,
                        "text": "Vaziyat va kayfiyatga qarab.",
                    },
                ],
            },
            {
                "gender": "groom",
                "section": "character_crisis",
                "order": 22,
                "text": "Ayolingiz sizdagi kamchilikni aytsa yoki tanqid qilsa reaksiyangiz?",
                "is_trap": False,
                "options": [
                    {
                        "letter": "A",
                        "weight": 10,
                        "text": "Bosiqlik bilan tinglayman, agar e'tiroz o‘rinli bo‘lsa, o‘zimni tuzataman.",
                    },
                    {
                        "letter": "B",
                        "weight": 9,
                        "text": "Bosiqlik bilan tinglayman, lekin o‘z pozitsiyam va sabablarimni tushuntiraman.",
                    },
                    {
                        "letter": "C",
                        "weight": 3,
                        "text": "Ranjiyman va ayolimga ham uning kamchiliklarini ko‘rsatib qo‘yaman.",
                    },
                    {
                        "letter": "D",
                        "weight": 1,
                        "text": "Tanqidni umuman yoqtirmayman.",
                    },
                ],
            },
            {
                "gender": "groom",
                "section": "character_crisis",
                "order": 23,
                "text": "Stress va ruhiy tushkunlikda ayolingizdan nima kutasiz?",
                "is_trap": False,
                "options": [
                    {
                        "letter": "A",
                        "weight": 6,
                        "text": "Meni yolg‘iz qoldirishini va tegmasligini.",
                    },
                    {
                        "letter": "B",
                        "weight": 10,
                        "text": "Yonimda bo‘lib, tinglashini va ma'naviy dalda berishini.",
                    },
                    {
                        "letter": "C",
                        "weight": 8,
                        "text": "Hissiyotlarga berilmay, amaliy maslahat berishini.",
                    },
                    {
                        "letter": "D",
                        "weight": 7,
                        "text": "Kayfiyatimni ko‘taradigan biror narsa qilishini.",
                    },
                ],
            },
            {
                "gender": "groom",
                "section": "character_crisis",
                "order": 24,
                "text": "Oilaviy muammolarni muhokama qilish uslubingiz?",
                "is_trap": False,
                "options": [
                    {
                        "letter": "A",
                        "weight": 7,
                        "text": "Darhol va issig‘ida hammasini ochiq-oydin gaplashib olish.",
                    },
                    {
                        "letter": "B",
                        "weight": 10,
                        "text": "Hissiyotlar va jahl bosilgach, 1-2 kundan keyin bosiqlik bilan gaplashish.",
                    },
                    {
                        "letter": "C",
                        "weight": 3,
                        "text": "Uchinchi shaxs orqali hal qilish.",
                    },
                    {
                        "letter": "D",
                        "weight": 2,
                        "text": "Vaqt o‘tishi bilan unutilib ketishini kutish.",
                    },
                ],
            },
            {
                "gender": "groom",
                "section": "future_plans",
                "order": 25,
                "text": "To‘ydan keyin farzand ko‘rish borasidagi rejangiz?",
                "is_trap": False,
                "options": [
                    {
                        "letter": "A",
                        "weight": 8,
                        "text": "Iloji boricha tezroq (Alloh qachon bersa).",
                    },
                    {
                        "letter": "B",
                        "weight": 10,
                        "text": "1-2 yil bir-birimizni tushunib, moliyaviy barqarorlashib keyin.",
                    },
                    {
                        "letter": "C",
                        "weight": 5,
                        "text": "Avval karyera/maqsadlarni amalga oshirib, keyin.",
                    },
                    {
                        "letter": "D",
                        "weight": 9,
                        "text": "Ayolim bilan birgalikda hal qilamiz.",
                    },
                ],
            },
            {
                "gender": "groom",
                "section": "future_plans",
                "order": 26,
                "text": "Farzand tarbiyasidagi asosiy shaxsiy uslubingiz?",
                "is_trap": False,
                "options": [
                    {
                        "letter": "A",
                        "weight": 7,
                        "text": "Qattiqqo‘llik, intizom va diniy ruhiyat.",
                    },
                    {
                        "letter": "B",
                        "weight": 10,
                        "text": "Do‘stona, tushunadigan va har qanday holatda qo‘llab-quvvatlaydigan.",
                    },
                    {
                        "letter": "C",
                        "weight": 6,
                        "text": "Erkinlik beradigan va mustaqil bo‘lishiga qo‘yib beradigan.",
                    },
                    {
                        "letter": "D",
                        "weight": 3,
                        "text": "Onasi tarbiya beradi, men faqat moddiy ta'minlayman.",
                    },
                ],
            },
            {
                "gender": "groom",
                "section": "future_plans",
                "order": 27,
                "text": "Erkak kishining uy ishlarida yordamlashishiga munosabatingiz?",
                "is_trap": False,
                "options": [
                    {
                        "letter": "A",
                        "weight": 3,
                        "text": "Uy ishlari — to‘liq ayolning vazifasi, men aralashmayman.",
                    },
                    {
                        "letter": "B",
                        "weight": 10,
                        "text": "Sunnatga muvofiq, imkon va bo‘sh vaqtim bo‘lganda yordam berib turaman.",
                    },
                    {
                        "letter": "C",
                        "weight": 7,
                        "text": "Uy ishlari teng 50/50 bo‘linishi kerak.",
                    },
                    {
                        "letter": "D",
                        "weight": 5,
                        "text": "Faqat ayolim kasal bo‘lganda yoki ulgurmagandagina yordam beraman.",
                    },
                ],
            },
            {
                "gender": "groom",
                "section": "future_plans",
                "order": 28,
                "text": "Dam olish kunlarini qanday o‘tkazishni afzal ko‘rasiz?",
                "is_trap": False,
                "options": [
                    {
                        "letter": "A",
                        "weight": 9,
                        "text": "Uyda, ayolim va oilam davrasida tinchlikda.",
                    },
                    {
                        "letter": "B",
                        "weight": 8,
                        "text": "Sayohatlarda, tabiat qo‘ynida va faol tarzda.",
                    },
                    {
                        "letter": "C",
                        "weight": 10,
                        "text": "Ota-onam va qarindoshlarimni ziyorat qilish bilan.",
                    },
                    {
                        "letter": "D",
                        "weight": 4,
                        "text": "Do‘stlarim va jamoatim bilan.",
                    },
                ],
            },
            {
                "gender": "groom",
                "section": "future_plans",
                "order": 29,
                "text": "Salomatlik (psixologik va jismoniy) borasidagi qarashingiz?",
                "is_trap": False,
                "options": [
                    {
                        "letter": "A",
                        "weight": 9,
                        "text": "Doimiy ravishda sport va to‘g‘ri ovqatlanishga e'tibor berish shart.",
                    },
                    {
                        "letter": "B",
                        "weight": 4,
                        "text": "Kasal bo‘lgandagina shifokorga murojaat qilish yetarli.",
                    },
                    {
                        "letter": "C",
                        "weight": 10,
                        "text": "Psixologik salomatlik va profilaktika juda muhim.",
                    },
                    {
                        "letter": "D",
                        "weight": 2,
                        "text": "Bunga alohida e'tibor bermayman.",
                    },
                ],
            },
            {
                "gender": "groom",
                "section": "future_plans",
                "order": 30,
                "text": "Oila qurganingizdan 5 yil o‘tib, eng katta yutug‘ingiz nima bo‘lishini xohlaysiz?",
                "is_trap": False,
                "options": [
                    {
                        "letter": "A",
                        "weight": 10,
                        "text": "Mustahkam iymonli oila, solih farzandlar va xonadonimda tinchlik.",
                    },
                    {
                        "letter": "B",
                        "weight": 7,
                        "text": "Shaxsiy uy-joy, mashina va moliyaviy erkinlik.",
                    },
                    {
                        "letter": "C",
                        "weight": 8,
                        "text": "Ayolim bilan birgalikda jamiyatda va sohamizda katta muvaffaqiyatga erishish.",
                    },
                    {
                        "letter": "D",
                        "weight": 10,
                        "text": "Bir-birimizga bo‘lgan muhabbat va hurmatimiz saqlanib qolgani.",
                    },
                ],
            },
            {
                "gender": "bride",
                "section": "religious_spiritual",
                "order": 1,
                "text": "Ibodat va hayot tarzi borasidagi shaxsiy amaliy holatingiz?",
                "is_trap": False,
                "options": [
                    {
                        "letter": "A",
                        "weight": 10,
                        "text": "Farz ibodatlarni (namoz, ro‘za) to‘liq ado etaman. Bo‘lajak oilamizda ham bu birinchi o‘rinda "
                        "bo‘lishini xohlayman.",
                    },
                    {
                        "letter": "B",
                        "weight": 8,
                        "text": "Ibodatlarni imkon qadar bajaraman, lekin ba'zan oqsaydigan vaqtlarim bo‘ladi. Majburlash va "
                        "bosimga qarshiman.",
                    },
                    {
                        "letter": "C",
                        "weight": 5,
                        "text": "Diniy amallarni to‘liq bajarmayman, lekin islomiy qadriyatlar va go‘zal axloqqa amal qilaman.",
                    },
                    {
                        "letter": "D",
                        "weight": 2,
                        "text": "Bu har kimning shaxsiy ishi, oilada diniy qarashlar muhokama qilinmasligi tarafdoriman.",
                    },
                ],
            },
            {
                "gender": "bride",
                "section": "religious_spiritual",
                "order": 2,
                "text": "Kiyinishingiz va hijobingiz borasida bo‘lajak eringizdan kutuvigiz?",
                "is_trap": False,
                "options": [
                    {
                        "letter": "A",
                        "weight": 10,
                        "text": "Shariatga muvofiq (hijobda) kiyinaman / to‘ydan keyin albatta hijobga kirish niyatidaman va "
                        "erim buni qo‘llab-quvvatlashini xohlayman.",
                    },
                    {
                        "letter": "B",
                        "weight": 8,
                        "text": "Hijobda emasman, lekin milliy va odob doirasida bosiq, iboli kiyinaman. Erim kiyimim uchun "
                        "doimiy bosim qilmasligini kutaman.",
                    },
                    {
                        "letter": "C",
                        "weight": 5,
                        "text": "Kiyinish uslubim o‘zimning erkin xohishim, bo‘lajak erim kiyimimga aralashmasligini "
                        "xohlayman.",
                    },
                    {
                        "letter": "D",
                        "weight": 2,
                        "text": "Zamonaviy uslubda kiyinaman va erim ham shunga mos munosabatda bo‘lishini kutaman.",
                    },
                ],
            },
            {
                "gender": "bride",
                "section": "religious_spiritual",
                "order": 3,
                "text": "TIZIM TUZOQ SAVOLI (Lie Scale - Samimiylikni aniqlash): Eringiz juda halol inson bo‘lsa-yu, lekin topishi "
                "oz bo‘lib, dugonalaringizning erlaridan moddiy tomondan orqada qolsangiz, ichki reaksiyangiz?",
                "is_trap": True,
                "options": [
                    {
                        "letter": "A",
                        "weight": 2,
                        "text": "Men umuman kibr qilmayman, hech qachon boshqalarga havas qilmaganman, faqat shukr qilaman. "
                        "(Puan: Yolg‘onlik indeksi oshadi)",
                    },
                    {
                        "letter": "B",
                        "weight": 10,
                        "text": "Ba'zan ichimda havas yoki siqilish bo‘ladi, lekin erimning halolligini qadrlab, unga "
                        "bildirmaslikka harakat qilaman. (Puan: Samimiy)",
                    },
                    {
                        "letter": "C",
                        "weight": 6,
                        "text": "Erimga ko‘proq harakat qilishini va topishini tushuntirib, talab qo‘yaman.",
                    },
                    {
                        "letter": "D",
                        "weight": 3,
                        "text": "O‘zim ham ishga kirib, yetishmovchilikni yopishga harakat qilaman.",
                    },
                ],
            },
            {
                "gender": "bride",
                "section": "religious_spiritual",
                "order": 4,
                "text": "Diniy va dunyoviy ta'limni er-xotin birgalikda oshirishiga munosabatingiz?",
                "is_trap": False,
                "options": [
                    {
                        "letter": "A",
                        "weight": 8,
                        "text": "Erim bilan birgalikda kitobxonlik va ilm olish darslarini yo‘lga qo‘yishni orzu qilaman.",
                    },
                    {
                        "letter": "B",
                        "weight": 10,
                        "text": "Har kim o‘zi mustaqil ilm olgani ma'qul, alohida maxsus jadvallarga hojat yo‘q.",
                    },
                    {
                        "letter": "C",
                        "weight": 7,
                        "text": "Faqat kasbiy va dunyoviy rivojlanishga e'tibor qaratishimiz kerak.",
                    },
                    {
                        "letter": "D",
                        "weight": 3,
                        "text": "Ilm olish bo‘sh vaqtga bog‘liq, bunga oilada alohida urg‘u bermayman.",
                    },
                ],
            },
            {
                "gender": "bride",
                "section": "religious_spiritual",
                "order": 5,
                "text": "Farzandlaringiz tarbiyasida eng birinchi poydevor nima bo‘lishini xohlaysiz?",
                "is_trap": False,
                "options": [
                    {
                        "letter": "A",
                        "weight": 10,
                        "text": "Diniy ta'lim va go‘zal Islomiy axloq.",
                    },
                    {
                        "letter": "B",
                        "weight": 7,
                        "text": "Zamonaviy bilimlar (chet dillari, IT) va mustaqil fikrlash.",
                    },
                    {
                        "letter": "C",
                        "weight": 6,
                        "text": "Sport va jismoniy salomatlik.",
                    },
                    {
                        "letter": "D",
                        "weight": 4,
                        "text": "Intizom va ota-onaga bo‘ysunish.",
                    },
                ],
            },
            {
                "gender": "bride",
                "section": "religious_spiritual",
                "order": 6,
                "text": "Erkak kishining oiladagi yetakchiligi (qavvomligi)ga munosabatingiz?",
                "is_trap": False,
                "options": [
                    {
                        "letter": "A",
                        "weight": 10,
                        "text": "Erkak kishi oilaning mutlaq rahbari, oxirgi qaror va mas'uliyat doim unda bo‘lishi kerak va "
                        "men unga bo‘ysunaman.",
                    },
                    {
                        "letter": "B",
                        "weight": 9,
                        "text": "Erkak kishi yetakchi, lekin barcha qarorlar er-xotin o‘rtasidagi teng huquqli maslahat bilan "
                        "qabul qilinadi.",
                    },
                    {
                        "letter": "C",
                        "weight": 5,
                        "text": "Oilada yetakchi yo‘q, barcha masalalarda to‘liq tenglik (demokratiya) bo‘lishi kerak.",
                    },
                    {
                        "letter": "D",
                        "weight": 3,
                        "text": "Vaziyatga qarab, kimgadir mas'uliyat topshiriladi.",
                    },
                ],
            },
            {
                "gender": "bride",
                "section": "financial_governance",
                "order": 7,
                "text": "Oilaviy ta'minot va topgan pulingiz borasida fikringiz?",
                "is_trap": False,
                "options": [
                    {
                        "letter": "A",
                        "weight": 10,
                        "text": "Erkak kishi oilani 100% ta'minlashi shart. Ayol kishining topgan puli faqat o‘ziga tegishli.",
                    },
                    {
                        "letter": "B",
                        "weight": 8,
                        "text": "Asosiy ta'minot erimning zimmasida bo‘ladi, lekin xohlasam va ishlasam, o‘z ixtiyorim bilan "
                        "ro‘zg‘orga yordam berishim mumkin.",
                    },
                    {
                        "letter": "C",
                        "weight": 5,
                        "text": "Byudjet umumiy bo‘lishi kerak, er-xotin birgalikda topib, birgalikda sarflaymiz.",
                    },
                    {
                        "letter": "D",
                        "weight": 3,
                        "text": "Kim ko‘proq topsa, o‘sha ko‘proq xarajatlarni qoplagani ma'qul.",
                    },
                ],
            },
            {
                "gender": "bride",
                "section": "financial_governance",
                "order": 8,
                "text": "To‘ydan keyin ishlashingiz yoki o‘qishingiz borasida kuyovdan kutuvigiz?",
                "is_trap": False,
                "options": [
                    {
                        "letter": "A",
                        "weight": 4,
                        "text": "Uyda o‘tirib, oila va farzandlar tarbiyasi bilan shug‘ullanishni afzal ko‘raman "
                        "(ishlamayman).",
                    },
                    {
                        "letter": "B",
                        "weight": 9,
                        "text": "Faqat ayollarga mos (ta'lim, tibbiyot va h.k.) va Islomiy shartlarga javob beradigan joyda "
                        "ishlashimga/o‘qishimga ruxsat berishini xohlayman.",
                    },
                    {
                        "letter": "C",
                        "weight": 7,
                        "text": "O‘z karyeramni qurishim va erkin ishlashim/o‘qishimga to‘sqinlik qilinmasligini kutaman.",
                    },
                    {
                        "letter": "D",
                        "weight": 5,
                        "text": "Faqat oilada moliyaviy ehtiyoj tug‘ilgandagina ishlaganim ma'qul deb hisoblayman.",
                    },
                ],
            },
            {
                "gender": "bride",
                "section": "financial_governance",
                "order": 9,
                "text": "Kunlik va oylik byudjetni kim boshqarishi kerak deb hisoblaysiz?",
                "is_trap": False,
                "options": [
                    {
                        "letter": "A",
                        "weight": 5,
                        "text": "Erkak kishi (pulning hammasi erimda turadi, menga ehtiyojimga qarab beradi).",
                    },
                    {
                        "letter": "B",
                        "weight": 9,
                        "text": "Ayol kishi (erim topgan pulini uyga beradi, xarajatlarni men taqsimlaydi).",
                    },
                    {
                        "letter": "C",
                        "weight": 10,
                        "text": "Erim bilan birgalikda rejalashtiramiz va hisob-kitobni birga olib boramiz.",
                    },
                    {
                        "letter": "D",
                        "weight": 3,
                        "text": "Aniq reja shart emas, ehtiyojga qarab sarflanaveradi.",
                    },
                ],
            },
            {
                "gender": "bride",
                "section": "financial_governance",
                "order": 10,
                "text": "Qarz yoki kredit olishga munosabatingiz qanday?",
                "is_trap": False,
                "options": [
                    {
                        "letter": "A",
                        "weight": 10,
                        "text": "Umuman qarz/kredit olishga qarshiman, erim bilan boriga qanoat qilib yashaymiz.",
                    },
                    {
                        "letter": "B",
                        "weight": 8,
                        "text": "Faqat juda zarur holatda (uy-joy yoki davolanish uchun) va foizsiz bo‘lsagina olish mumkin.",
                    },
                    {
                        "letter": "C",
                        "weight": 4,
                        "text": "Biznes va maqsadlar uchun bank kreditlaridan foydalanishni normal holat deb bilaman.",
                    },
                    {
                        "letter": "D",
                        "weight": 2,
                        "text": "Sharoitga qarab, tezroq natijaga erishish uchun qarz olishdan qochmaslik kerak.",
                    },
                ],
            },
            {
                "gender": "bride",
                "section": "financial_governance",
                "order": 11,
                "text": "Katta xarajatlar (mashina, mebel, ta'til) bo‘yicha qaror qanday olinishini xohlaysiz?",
                "is_trap": False,
                "options": [
                    {
                        "letter": "A",
                        "weight": 4,
                        "text": "Erkak kishi sifatida erim bir o‘zi qaror qiladi.",
                    },
                    {
                        "letter": "B",
                        "weight": 8,
                        "text": "Men bilan maslahatlashadi, lekin oxirgi so‘zni erim aytadi.",
                    },
                    {
                        "letter": "C",
                        "weight": 10,
                        "text": "Ikkalamiz ham bir ovozdan rozi bo‘lgandagina xarid qilinadi.",
                    },
                    {
                        "letter": "D",
                        "weight": 3,
                        "text": "Pul kimniki bo‘lsa, qarorni ham o‘sha qabul qiladi.",
                    },
                ],
            },
            {
                "gender": "bride",
                "section": "financial_governance",
                "order": 12,
                "text": "TIZIM TUZOQ SAVOLI (Sabr va Moliya testi): Eringiz kasal bo‘lib yoki ishidan ayrilib, 6 oy uyda qolib "
                "ketganida, harakatlaringiz?",
                "is_trap": True,
                "options": [
                    {
                        "letter": "A",
                        "weight": 8,
                        "text": "Bir og‘iz ham nolimasdan sabr qilaman va uni ma'naviy qo‘llab-quvvatlayman.",
                    },
                    {
                        "letter": "B",
                        "weight": 10,
                        "text": "Bosiqlik bilan tushuntirib, birgalikda yechim yoki unga yangi ish qidiramiz.",
                    },
                    {
                        "letter": "C",
                        "weight": 6,
                        "text": "O‘zim ishga kirib, ro‘zg‘orni va erimni ta'minlayman.",
                    },
                    {
                        "letter": "D",
                        "weight": 2,
                        "text": "Ota-onamnikiga borib turaman yoki ulardan yordam so‘rayman.",
                    },
                ],
            },
            {
                "gender": "bride",
                "section": "relatives_relations",
                "order": 13,
                "text": "To‘ydan keyin yashash joyi borasida xohishingiz/rejangiz?",
                "is_trap": False,
                "options": [
                    {
                        "letter": "A",
                        "weight": 5,
                        "text": "Doimiy ravishda qaynona-qaynotam bilan birga yashash va ularning xizmatini qilib duosini "
                        "olish.",
                    },
                    {
                        "letter": "B",
                        "weight": 8,
                        "text": "Dastlab qaynona-qaynotam bilan yashab, keyinchalik sharoit bo‘lsa alohida chiqish.",
                    },
                    {
                        "letter": "C",
                        "weight": 9,
                        "text": "To‘ydan darhol erim bilan alohida (ijarada yoki o‘z uyimizda) yashash.",
                    },
                    {
                        "letter": "D",
                        "weight": 10,
                        "text": "Vaziyatga va erimning ota-onasining ehtiyojiga qarab hal qilinishi tarafdoriman.",
                    },
                ],
            },
            {
                "gender": "bride",
                "section": "relatives_relations",
                "order": 14,
                "text": "Qaynona va kelin munosabatlarida nohaqlik bo‘lsa, pozitsiyangiz?",
                "is_trap": False,
                "options": [
                    {
                        "letter": "A",
                        "text": 'Qaynonam nohaq bo‘lsalar ham "xo‘p bo‘ladi" deb indamayman, duolarini olaman.',
                    },
                    {
                        "letter": "B",
                        "weight": 10,
                        "text": "O‘sha joyda indamayman, lekin keyin erimga alohida qolganda bosiqlik bilan tushuntirib "
                        "beraman.",
                    },
                    {
                        "letter": "C",
                        "weight": 7,
                        "text": "O‘zimning haq ekanligimni qaynonamga odob bilan darhol tushuntirishga harakat qilaman.",
                    },
                    {
                        "letter": "D",
                        "weight": 6,
                        "text": "O‘z ota-onamga aytib, ularni aralashtiraman.",
                    },
                ],
            },
            {
                "gender": "bride",
                "section": "relatives_relations",
                "order": 15,
                "text": "TIZIM TUZOQ SAVOLI (Qaynona va Ota-ona balansi - Cross Validation): Qaynonangiz va o‘z onangizning "
                "qarashlari bir-biriga qarama-qarshi kelib qolsa, kimning gapiga amal qilasiz?",
                "is_trap": True,
                "options": [
                    {
                        "letter": "A",
                        "weight": 3,
                        "text": "Qaynonamning gapiga, chunki endi u kishi mening asosiy onam hisoblanadi.",
                    },
                    {
                        "letter": "B",
                        "weight": 10,
                        "text": "Erim bilan maslahatlashib, ikkala tarafni ham ranjitmaydigan o'rta yo'lni izlayman.",
                    },
                    {
                        "letter": "C",
                        "weight": 6,
                        "text": "O‘z onamning gapiga, chunki u kishi men uchun birinchi o‘rinda.",
                    },
                    {
                        "letter": "D",
                        "weight": 2,
                        "text": "Vaziyatga va kimning gapi mantiqliroq ekaniga qarayman.",
                    },
                ],
            },
            {
                "gender": "bride",
                "section": "relatives_relations",
                "order": 16,
                "text": "Oilaviy tushunmovchilik va eringiz bilan bo‘lgan sirlarni kimga aytishingiz mumkin?",
                "is_trap": False,
                "options": [
                    {
                        "letter": "A",
                        "weight": 10,
                        "text": "Hech kimga! Muammo va sirlar faqat men va erim o‘rtasida qolishi shart.",
                    },
                    {
                        "letter": "B",
                        "weight": 8,
                        "text": "Faqat juda chidab bo‘lmas holatdagina o‘z ota-onamga yoki xolis xakamga (psixolog/domla) "
                        "murojaat qilaman.",
                    },
                    {
                        "letter": "C",
                        "weight": 3,
                        "text": "O‘z ota-onam va yaqin dugonalarim bilan maslahatlashib turaman.",
                    },
                    {
                        "letter": "D",
                        "weight": 4,
                        "text": "Kimga aytishni vaziyat ko‘rsatadi.",
                    },
                ],
            },
            {
                "gender": "bride",
                "section": "relatives_relations",
                "order": 17,
                "text": "O‘z ota-onangiznikiga borib-kelish tartibi?",
                "is_trap": False,
                "options": [
                    {
                        "letter": "A",
                        "weight": 4,
                        "text": "Qaynona-qaynotam va erim qachon ruxsat bersa va belgilab qo‘ysa, o‘shanda boraman.",
                    },
                    {
                        "letter": "B",
                        "weight": 10,
                        "text": "Belgilangan kunlarda (masalan, haftada 1 marta) erim bilan birga borib kelamiz.",
                    },
                    {
                        "letter": "C",
                        "weight": 6,
                        "text": "Xohlagan paytimda o‘z ota-onamnikiga borish huquqiga egaman.",
                    },
                    {
                        "letter": "D",
                        "weight": 8,
                        "text": "Uy ishlaridan bo‘shaganimizdagina boraman.",
                    },
                ],
            },
            {
                "gender": "bride",
                "section": "relatives_relations",
                "order": 18,
                "text": "Kelinlik majburiyatlari (xizmat, urf-odatlar)ga shaxsiy munosabatingiz?",
                "is_trap": False,
                "options": [
                    {
                        "letter": "A",
                        "weight": 5,
                        "text": "Milliy urf-odatlar va kelinlik xizmatlarini to‘liq bajarishga tayyorman.",
                    },
                    {
                        "letter": "B",
                        "weight": 10,
                        "text": "Faqat Islomda bor va insoniylik doirasidagi xizmatlarni qilaman, ortiqcha urf-odatlarga hojat "
                        "yo‘q.",
                    },
                    {
                        "letter": "C",
                        "weight": 8,
                        "text": "Kelin — xizmatkor emas, teng huquqli oila a'zosi. Barcha ishlar bo‘lishib qilinishi kerak.",
                    },
                    {
                        "letter": "D",
                        "weight": 4,
                        "text": "Urf-odatlarga unchalik e'tibor bermayman.",
                    },
                ],
            },
            {
                "gender": "bride",
                "section": "character_crisis",
                "order": 19,
                "text": "TIZIM TUZOQ SAVOLI (Jahl va Emotsiya boshqaruvi - Lie Scale): Eringiz sababsiz sizga baqirsa yoki "
                "kayfiyatingizni buzsa, reaksiyangiz?",
                "is_trap": True,
                "options": [
                    {
                        "letter": "A",
                        "weight": 2,
                        "text": "Men hech qachon xafa bo‘lmayman va jahlim chiqmaydi, doim kulib turaman. (Puan: Yolg‘onlik "
                        "indeksi oshadi)",
                    },
                    {
                        "letter": "B",
                        "weight": 10,
                        "text": "Ichimdan ranjiyman va yig‘lab olishim mumkin, lekin janjal qilmay, tinchlanishini kutaman. "
                        "(Puan: Samimiy)",
                    },
                    {
                        "letter": "C",
                        "weight": 7,
                        "text": "O‘sha joyning o‘zida men ham e'tiroz bildirib, haq ekanligimni isbotlayman.",
                    },
                    {
                        "letter": "D",
                        "weight": 2,
                        "text": "Boshqa xonaga o‘tib olib, uzoq vaqt gaplashmay yuraman.",
                    },
                ],
            },
            {
                "gender": "bride",
                "section": "character_crisis",
                "order": 20,
                "text": "Eringiz bilan tushunmovchilik bo‘lganda birinchi bo‘lib kim qadam tashlashi kerak?",
                "is_trap": False,
                "options": [
                    {
                        "letter": "A",
                        "weight": 10,
                        "text": "Oilamizda tinchlik saqlanishi uchun, kim haq bo‘lishidan qat'i nazar, birinchi bo‘lib yon "
                        "bosaman.",
                    },
                    {
                        "letter": "B",
                        "weight": 5,
                        "text": "Faqat haqiqiy aybdor taraf xatosini tan olib, birinchi qadamni tashlashi kerak.",
                    },
                    {
                        "letter": "C",
                        "weight": 4,
                        "text": "Erkak kishi oilada katta bo‘lgani uchun har doim birinchi qadamni tashlab, ko‘nglimni olishi "
                        "kerak.",
                    },
                    {
                        "letter": "D",
                        "weight": 3,
                        "text": "Vaqt o‘zi hammasini joyiga solishini kutaman.",
                    },
                ],
            },
            {
                "gender": "bride",
                "section": "character_crisis",
                "order": 21,
                "text": "Shaxsiy hudud va dugonalar bilan ko‘rishishga munosabatingiz?",
                "is_trap": False,
                "options": [
                    {
                        "letter": "A",
                        "weight": 10,
                        "text": "To‘ydan keyin dugonalar bilan uchrashuvlar va ortiqcha xobbilar ikkinchi darajaga o‘tishi yoki "
                        "to‘xtashi kerak.",
                    },
                    {
                        "letter": "B",
                        "weight": 9,
                        "text": "Erimdan ruxsat olgan holda, oilamga va ro‘zg‘orimga zarar yetkazmagan tarzda me'yorida vaqt "
                        "ajrataman.",
                    },
                    {
                        "letter": "C",
                        "weight": 3,
                        "text": "Dugonalarim va shaxsiy vaqtim daxlsiz bo‘lishi, erim bunaqa narsalarni cheklamasligi shart.",
                    },
                    {
                        "letter": "D",
                        "weight": 5,
                        "text": "Erim qayerga borsa va qanday ruxsat bersa, shunga moslashaman.",
                    },
                ],
            },
            {
                "gender": "bride",
                "section": "character_crisis",
                "order": 22,
                "text": "Eringiz sizdagi kamchilikni aytsa yoki tanqid qilsa reaksiyangiz?",
                "is_trap": False,
                "options": [
                    {
                        "letter": "A",
                        "weight": 10,
                        "text": "Og‘rinmay, minnatdorchilik bilan qabul qilaman va darhol o‘zim ustimda ishlayman.",
                    },
                    {
                        "letter": "B",
                        "weight": 9,
                        "text": "Bosiqlik bilan tinglayman, lekin agar nohaq bo‘lsa, o‘zimni bosiqlik bilan tushuntiraman.",
                    },
                    {
                        "letter": "C",
                        "weight": 3,
                        "text": "Ranjiyman, xafa bo‘lib ichimga solaman va erimga ham uning kamchiligini eslataman.",
                    },
                    {
                        "letter": "D",
                        "weight": 1,
                        "text": "Tanqidni umuman yoqtirmayman va menga tanbeh berilishiga qarshiman.",
                    },
                ],
            },
            {
                "gender": "bride",
                "section": "character_crisis",
                "order": 23,
                "text": "Qattiq tushkunlik (stress) holatida eringizdan nima kutasiz?",
                "is_trap": False,
                "options": [
                    {
                        "letter": "A",
                        "weight": 6,
                        "text": "Meni biroz yolg‘iz qoldirishini va o‘zimga kelib olishimga imkon berishini.",
                    },
                    {
                        "letter": "B",
                        "weight": 10,
                        "text": "Shunchaki yonimda bo‘lib, meni tinglashini, bag‘riga bosib ma'naviy dalda berishini.",
                    },
                    {
                        "letter": "C",
                        "weight": 8,
                        "text": "Hissiyotlarga berilmay, muammoni hal qilish uchun aniq va amaliy maslahat berishini.",
                    },
                    {
                        "letter": "D",
                        "weight": 7,
                        "text": "Kayfiyatimni ko‘taradigan biror syurpriz yoki xarid qilib berishini.",
                    },
                ],
            },
            {
                "gender": "bride",
                "section": "character_crisis",
                "order": 24,
                "text": "Oilaviy muammolarni muhokama qilish uslubingiz?",
                "is_trap": False,
                "options": [
                    {
                        "letter": "A",
                        "weight": 7,
                        "text": "Darhol va issig‘ida hammasini ochiq-oydin gaplashib olish.",
                    },
                    {
                        "letter": "B",
                        "weight": 10,
                        "text": "Hissiyotlar va jahl bosilgach, 1-2 kundan keyin bosiqlik bilan gaplashish.",
                    },
                    {
                        "letter": "C",
                        "weight": 3,
                        "text": "Uchinchi shaxs orqali hal qilish.",
                    },
                    {
                        "letter": "D",
                        "weight": 2,
                        "text": "Vaqt o‘tishi bilan o‘zi unutilib ketishini kutish.",
                    },
                ],
            },
            {
                "gender": "bride",
                "section": "future_plans",
                "order": 25,
                "text": "To‘ydan keyin farzand ko‘rish borasidagi xohishingiz/rejangiz?",
                "is_trap": False,
                "options": [
                    {
                        "letter": "A",
                        "weight": 8,
                        "text": "Iloji boricha tezroq (Alloh qachon bergan kuni).",
                    },
                    {
                        "letter": "B",
                        "weight": 10,
                        "text": "1-2 yil bir-birimizni yaxshiroq bilib va yangi oilaga moslashib keyin.",
                    },
                    {
                        "letter": "C",
                        "weight": 5,
                        "text": "Avval o‘qishimni/karyeramni tugatib, keyin farzandli bo‘lish.",
                    },
                    {
                        "letter": "D",
                        "weight": 9,
                        "text": "Buni to‘ydan keyin erim bilan birgalikda maslahatlashib hal qilamiz.",
                    },
                ],
            },
            {
                "gender": "bride",
                "section": "future_plans",
                "order": 26,
                "text": "Farzandlaringiz tarbiyasidagi asosiy shaxsiy uslubingiz?",
                "is_trap": False,
                "options": [
                    {
                        "letter": "A",
                        "weight": 7,
                        "text": "Qattiqqo‘llik va qat'iy intizom orqali.",
                    },
                    {
                        "letter": "B",
                        "weight": 10,
                        "text": "Do‘stona, tushunishga va mehrga asoslangan munosabat orqali.",
                    },
                    {
                        "letter": "C",
                        "weight": 6,
                        "text": "Erkinlik berish va o‘z xatolaridan o‘zi saboq olishiga imkon yaratish.",
                    },
                    {
                        "letter": "D",
                        "weight": 3,
                        "text": "Faqat Islomiy manbalarga va sunnatga tayanib tarbiya berish.",
                    },
                ],
            },
            {
                "gender": "bride",
                "section": "future_plans",
                "order": 27,
                "text": "Eringizning uy ishlarida yordamlashishiga munosabatingiz?",
                "is_trap": False,
                "options": [
                    {
                        "letter": "A",
                        "weight": 3,
                        "text": "Uy ishlari — to‘liq ayol kishining vazifasi, erim aralashmasligi kerak deb hisoblayman.",
                    },
                    {
                        "letter": "B",
                        "weight": 10,
                        "text": "Sunnatga muvofiq, erimning imkon va bo‘sh vaqti bo‘lganda yordam berishi go‘zal ish.",
                    },
                    {
                        "letter": "C",
                        "weight": 7,
                        "text": "Uy ishlari va ro‘zg‘or yuki teng (50/50) bo‘linishi shart.",
                    },
                    {
                        "letter": "D",
                        "weight": 5,
                        "text": "Faqat kasal bo‘lib qolganimda yoki ulgurmay qolganimdagina yordam berishi yetarli.",
                    },
                ],
            },
            {
                "gender": "bride",
                "section": "future_plans",
                "order": 28,
                "text": "Hordiq chiqarish va dam olish kunlarini qanday o‘tkazishni afzal ko‘rasiz?",
                "is_trap": False,
                "options": [
                    {
                        "letter": "A",
                        "weight": 9,
                        "text": "Uyda, erim va oilamiz davrasida tinchlikda.",
                    },
                    {
                        "letter": "B",
                        "weight": 8,
                        "text": "Tabiat qo‘ynida, sayohatlarda va faol tarzda.",
                    },
                    {
                        "letter": "C",
                        "weight": 10,
                        "text": "Qaynona-qaynota hamda ota-onamizni ziyorat qilish bilan.",
                    },
                    {
                        "letter": "D",
                        "weight": 4,
                        "text": "Dugonalar va yaqinlarim bilan.",
                    },
                ],
            },
            {
                "gender": "bride",
                "section": "future_plans",
                "order": 29,
                "text": "Salomatligingiz (psixologik va jismoniy) borasidagi shaxsiy qarashingiz?",
                "is_trap": False,
                "options": [
                    {
                        "letter": "A",
                        "weight": 9,
                        "text": "Doimiy ravishda sport va to‘g‘ri ovqatlanishga e'tibor berishim shart.",
                    },
                    {
                        "letter": "B",
                        "weight": 4,
                        "text": "Kasal bo‘lib qolganimdagina shifokorga murojaat qilish yetarli deb bilaman.",
                    },
                    {
                        "letter": "C",
                        "weight": 10,
                        "text": "Psixologik salomatlik, ichki xotirjamlik va profilaktika juda muhim.",
                    },
                    {
                        "letter": "D",
                        "weight": 2,
                        "text": "Bunga alohida vaqt va e'tibor ajratmayman.",
                    },
                ],
            },
            {
                "gender": "bride",
                "section": "future_plans",
                "order": 30,
                "text": "Oila qurganingizdan 5 yil o‘tib, eng katta yutug‘ingiz nima bo‘lishini xohlaysiz?",
                "is_trap": False,
                "options": [
                    {
                        "letter": "A",
                        "weight": 10,
                        "text": "Erimning roziligini olgan baxtli kelin, mustahkam iymonli oila va solih/soliha farzandlarning "
                        "onasi bo‘lish.",
                    },
                    {
                        "letter": "B",
                        "weight": 7,
                        "text": "Shaxsiy uy-joy, mashina va moliyaviy erkinlikka erishgan oila bo‘lish.",
                    },
                    {
                        "letter": "C",
                        "weight": 8,
                        "text": "Erim ikkalamizning ham o‘z sohamizda va jamiyatda erishgan muvaffaqiyatimiz.",
                    },
                    {
                        "letter": "D",
                        "weight": 10,
                        "text": "Erim bilan bir-birimizga bo‘lgan muhabbat va hurmatimiz saqlanib qolgani.",
                    },
                ],
            },
        ]

        SECTION_NAME_MAP = {
            "religious_spiritual": "I. Diniy-Ma'naviy Qadriyatlar va E'tiqod",
            "financial_governance": "II. Oila Boshqaruvi va Moliyaviy Qarashlar",
            "relatives_relations": "III. Qarindoshlar va Qaynona-Kelin Munosabatlari",
            "character_crisis": "IV. Harakter, Psixologik Muvofiqlik va Inqiroz",
            "future_plans": "V. Kelajak Rejalari va Maishiy Hayot",
        }

        section_type_map = {}
        for code, name in SECTION_NAME_MAP.items():
            sec_obj, _ = SectionType.objects.get_or_create(name=name)
            section_type_map[code] = sec_obj

        existing_questions = {
            (q.target_gender, q.order): q for q in Question.objects.all()
        }

        questions_to_create = []
        data_to_process = []

        for item in questions_data:
            sec_code = item["section"]
            sec_instance = section_type_map.get(sec_code)
            if not sec_instance:
                sec_instance, _ = SectionType.objects.get_or_create(name=sec_code)

            key = (item["gender"], item["order"])

            if key not in existing_questions:
                q_obj = Question(
                    section=sec_instance,
                    text=item["text"],
                    target_gender=item["gender"],
                    is_trap_question=item["is_trap"],
                    order=item["order"],
                )
                questions_to_create.append(q_obj)
                data_to_process.append((q_obj, item["options"]))
            else:
                q_obj = existing_questions[key]
                data_to_process.append((q_obj, item["options"]))

        created_questions = []
        if questions_to_create:
            created_questions = Question.objects.bulk_create(questions_to_create)
            self.stdout.write(
                f"{len(created_questions)} ta yangi savol bazaga qo'shildi."
            )
        else:
            self.stdout.write("Barcha savollar allaqachon bazada mavjud.")

        all_question_ids = [q.id for q, _ in data_to_process if q.id]
        existing_options_dict = {
            (opt.question_id, opt.option_letter): opt
            for opt in QuestionOption.objects.filter(question_id__in=all_question_ids)
        }

        DEFAULT_WEIGHTS = {"A": 10, "B": 7, "C": 4, "D": 1}

        options_to_create = []
        options_to_update = []

        for q_obj, options_list in data_to_process:
            for opt in options_list:
                opt_key = (q_obj.id, opt["letter"])
                target_weight = opt.get("weight", DEFAULT_WEIGHTS.get(opt["letter"], 0))

                if opt_key not in existing_options_dict:
                    options_to_create.append(
                        QuestionOption(
                            question=q_obj,
                            option_letter=opt["letter"],
                            text=opt["text"],
                            weight=target_weight,
                        )
                    )
                else:
                    existing_opt = existing_options_dict[opt_key]
                    if existing_opt.weight == 0 or opt.get("weight") is not None:
                        existing_opt.weight = target_weight
                        options_to_update.append(existing_opt)

        created_options = []
        if options_to_create:
            created_options = QuestionOption.objects.bulk_create(options_to_create)
            self.stdout.write(
                f"{len(created_options)} ta yangi variant bazaga qo'shildi."
            )
        else:
            self.stdout.write("Barcha variantlar allaqachon bazada mavjud.")

        if options_to_update:
            QuestionOption.objects.bulk_update(options_to_update, fields=["weight"])
            self.stdout.write(
                f"{len(options_to_update)} ta variant vaznlari (weight) yangilandi."
            )

        self.stdout.write(
            self.style.SUCCESS(
                f"Jarayon yakunlandi! {len(created_questions)} ta yangi savol va {len(created_options)} ta yangi variant yaratildi."
            )
        )
