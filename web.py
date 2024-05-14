import streamlit as st
from streamlit_option_menu import option_menu
import joblib
import pandas as pd
import folium
from streamlit_folium import st_folium
import plotly.express as px
from streamlit_folium import folium_static


with st.sidebar:
    selected = option_menu("Недвижимость Нью-Йорка", ["Главное","Нью Йорк и его районы",
                                                      "Виды недвижимости Нью-Йорка",
                                                      'Анализ недвижимости Нью-Йорка',
                                                      "Карта свободной недвижимости",
                                                      "Подобрать недвижимость",
                                                      "Рассчитать стоимость и определить класс недвижимости",
                                                    "Модели"], 
        icons=['cast', 'house','building','briefcase','map','cloud','cash','gear'], menu_icon = 'cast', 
        default_index=0, orientation="horizontal")














###------------------------------------------------------------------------------------------------------------------------------
### Построение модели прогноза
if selected == 'Рассчитать стоимость и определить класс недвижимости':
    def user_input_features():
        type_options = ('Co-op', 'House', 'Condo', 'Multi-family home', 'Condop', 'Townhouse', 'Land')
        district_options = ('Queens', 'New York', 'Kings', 'Richmond', 'Bronx')

        type = st.selectbox('Выберите тип дома', type_options)
        
        if type == 'Land':
            # Если тип дома - "Land", заполняем остальные поля значениями по умолчанию (1)
            district = st.sidebar.selectbox('Район', district_options)
            close_to_sights = st.sidebar.selectbox('Близость к достопримечательностям', ('Да', 'Нет'))
            close_to_sights = 1 if close_to_sights == 'Да' else 0
            
            data = {'TYPE': type,
                    'BEDS': 1,  
                    'BATH': 1,  
                    'PROPERTYSQFT': 1,  
                    'District': district,
                    'Close to the sights': close_to_sights}
        else:
            # Если тип дома не "Land", получаем ввод пользователя для всех полей
            bed = st.number_input('Введите количество спальных комнат', step=1, min_value=1, max_value=100)
            bath = st.number_input('Введите количество ванных комнат', step=1, min_value=1, max_value=100)
            sqft = st.number_input('Введите размер площади в квадратных метрах', step=1, min_value=20, max_value=9999)
            district = st.selectbox('Район', district_options)
            close_to_sights = st.selectbox('Близость к достопримечательностям', ('Да', 'Нет'))
            close_to_sights = 1 if close_to_sights == 'Да' else 0

            data = {'TYPE': type,
                    'BEDS': bed,
                    'BATH': bath,
                    'PROPERTYSQFT': sqft,
                    'District': district,
                    'Close to the sights': close_to_sights}
        
        features = pd.DataFrame(data, index=[0])
        return features

    def load_data():
        data_predict = pd.read_excel('X_example.xlsx', index_col=None).drop(['Unnamed: 0','PRICE'], axis=1)
        data = pd.read_excel('X_example.xlsx').drop('Unnamed: 0', axis=1)
        extra_features = pd.read_excel('Extra Features.xlsx', index_col=None)
        return data_predict, data, extra_features

    def preprocess_data_for_regression(input_df, data_predict, extra_features):
        input_df = input_df.merge(extra_features, on='District', how='left')
        df = pd.concat([input_df, data_predict], axis=0)
        df = pd.get_dummies(df, columns=['District', 'TYPE'], drop_first=True, prefix=None)
        X = df[:1]
        return X

    def preprocess_data_for_clustering(prediction, input_df, extra_features):
        prediction = pd.DataFrame({'PRICE': prediction})
        X_cluster = pd.concat([prediction, input_df], axis=1)
        X_cluster = X_cluster.merge(extra_features, on='District', how='left')

        return X_cluster

    def predict_price(X):
        model_cat = joblib.load('Catboost_Regression.pkl')
        prediction = model_cat.predict(X)

        return prediction

    def cluster_data(X_clustering, data):
        data_kmeans = pd.concat([X_clustering, data], axis=0)
        data_kmeans = pd.get_dummies(data_kmeans, columns=['District', 'TYPE'], drop_first=True, prefix=None)
        model_kmeans = joblib.load('Kmeans.pkl')
        clusters = model_kmeans.predict(data_kmeans)
        data_kmeans['cluster'] = clusters

        return data_kmeans

    def categorize_clusters(data_kmeans):
        mean_df = data_kmeans.groupby('cluster').mean()
        elite_category_kmeans = mean_df['PRICE'].idxmax()
        economic_category_kmeans = mean_df['PRICE'].idxmin()
        comfort_category_kmeans = mean_df[mean_df['PRICE'] > mean_df['PRICE'].loc[economic_category_kmeans]].idxmin()['PRICE']
        business_category_kmeans = mean_df[mean_df['PRICE'] < mean_df['PRICE'].loc[elite_category_kmeans]].idxmax()['PRICE']
        data_kmeans['kmeans_category'] = data_kmeans['cluster'].map({
            elite_category_kmeans: 'Элитный',
            economic_category_kmeans: 'Эконом',
            comfort_category_kmeans: 'Комфорт',
            business_category_kmeans: 'Бизнес'
        })
        return data_kmeans


    def main():
        st.title('Прогнозирование цен на недвижимость')
        input_df = user_input_features()

        data_predict, data, extra_features = load_data()

        X_regression = preprocess_data_for_regression(input_df, data_predict, extra_features)
        
        if st.button('Получить результат модели'):
            prediction = predict_price(X_regression)
            X_clustering = preprocess_data_for_clustering(prediction, input_df, extra_features)
            data_kmeans = cluster_data(X_clustering, data)
            data_kmeans = categorize_clusters(data_kmeans)

            st.subheader('Результаты прогноза и категория дома')
            if input_df['TYPE'].values[0] != 'Land':  # Проверяем тип дома
                if prediction < 0:
                    st.warning('Недопустимые параметры, выберете другие 🔥')
                else:
                    st.success(f'Прогнозируемая цена: {round(prediction[0])}$')
                    st.success(f'Ожидаемая категория дома: {data_kmeans["kmeans_category"][:1].values[0]}')
            else:
                if prediction[0] < 0:
                    st.warning('Недопустимые параметры, выберете другие 🔥')
                else:
                    st.success(f'Прогнозируемая цена: {round(prediction[0])}$')

    if __name__ == "__main__":
        main()














###------------------------------------------------------------------------------------------------------------------------------
### Описание недвижимости в Нью-Йорке
elif selected == 'Виды недвижимости Нью-Йорка':
    st.title("Виды недвижимости Нью-Йорка")

    st.header("Co-op (кооператив)")

    st.markdown("""
    Кооператив - это структура, в которой компания владеет всем зданием и правами собственности на него. Покупатель или домовладелец, по сути, является акционером компании, а не владельцем недвижимости, и когда он приобретает акции компании, он заключает с ней договор аренды. Другими словами, покупатель фактически приобретает акции компании и право на проживание в здании конкретных арендаторов. Именно поэтому владельцы кооперативов сдают свои дома в субаренду или в аренду второму арендодателю, поскольку эти владельцы по своей природе являются арендаторами.

    Цены на кооперативную недвижимость обычно гораздо ниже, чем на кондоминиумы, и в Нью-Йорке они составляют большую часть, более 90% в прошлом и почти 70% сейчас. На заре становления Нью-Йорка большинство недвижимости было кооперативной, и большинство элитной недвижимости было кооперативной, а кондоминиумы появились позже, поэтому многие старые и лучшие районы, такие как Пятая авеню, были в основном кооперативными. Но время изменилось, и кондоминиумы догнали и стали предпочтительным выбором большинства покупателей, значительно опередив кондоминиумы по цене и росту стоимости.
    """)

    st.image('Photos/co-op.jpeg', caption = 'Фотография Co-op')


    st.header("House (Дом)")

    st.markdown("""
    Дома в Нью-Йорке представляют собой значительную часть рынка недвижимости города, хотя они чаще встречаются в пригородных районах, таких как Стейтен-Айленд, Бруклин, Квинс и Бронкс, где доступнее цены на жилье и есть больше пространства для застройки. В Манхэттене и частях Бруклина такие дома встречаются реже из-за ограниченного пространства и высокой стоимости земли.

    Цены на дома в Нью-Йорке могут сильно варьироваться в зависимости от местоположения, размера и состояния дома, а также от наличия дополнительных удобств, таких как дворы или парковочные места. Обычно цены на дома выше, чем на квартиры в многоэтажных зданиях, особенно в более престижных районах.            
                """)

    st.image('Photos/house.jpeg', caption = 'Фотография House')


    st.header("Condo (Кондоминиум)")

    st.markdown("""
    Нью-Йорк, особенно Манхэттен, долгое время был домом для беднейших из бедных. По мере того как в город прибывали волны иммигрантов и рос средний класс, многие люди покидали город и перебирались в пригороды. Остались лишь жители Манхэттена с высоким уровнем преступности и низким уровнем дохода. Но с 80-х годов прошлого века Манхэттен стал быстро обгонять пригороды, а доходы местных жителей росли с каждым годом.

    Кондоминиумы начали появляться в Нью-Йорке в 1960-х годах и быстро стали приоритетом в последующее десятилетие благодаря высокой степени свободы покупки, продажи и аренды. Благодаря тому, что Нью-Йорк вновь стал глобальным городом, а на зарубежных покупателей приходится около 35 % нью-йоркской недвижимости, кондоминиумы, несомненно, являются главным выбором.

    Покупателей кондоминиумов значительно больше, чем покупателей кооперативных квартир, а цены гораздо выше, что заставляет застройщиков охотнее приобретать землю по завышенной цене, чтобы построить более доступный и высокодоходный кондоминиум.

    Кондоминиумы оформляются в индивидуальную собственность, что означает, что покупатель или владелец владеет документом и правом собственности на недвижимость, а площадь кондоминиума в Нью-Йорке обычно учитывается только как внутренняя/внутренняя площадь, а общая или совместная площадь очень мала, обычно менее 1 %. Важно отметить, что расчет внутренней площади зависит от используемого метода. Например, метод, используемый геодезистом и застройщиком, может отличаться, например, иногда существует большое расхождение между расчетом центра стены и расчетом абсолютной площади интерьера.
                """)
    
    st.image('Photos/condo.jpeg', caption = 'Фотография Condo')


    st.header('Multi-family home (Многосемейный дом)')

    st.markdown("""
    Многоквартирный дом принадлежит одному владельцу, но имеет несколько законных кухонь, и по закону может сдаваться в аренду нескольким семьям.

    Поскольку здесь нет соседской ассоциации, для сдачи в аренду или продажи не требуется никаких заявлений, только согласие владельца.

    В целом, качество многоквартирных домов несколько ниже, чем односемейных, но доходность инвестиций выше.
                """)
    
    st.image('Photos/multifamilyhome.jpeg', caption = 'Фотография Multi-family home')


    st.header('Condop (Кондоп)')

    st.markdown("""
    Condop - это комбинация Condo и Co-Op.

    Condop - это, как правило, коммерческие кондоминиумы на 1-3 этажах, а Co-Op - жилые кондоминиумы на верхних этажах, которые отличаются от Co-Op тем, что Condop обычно продаются и сдаются в аренду как кондоминиумы. Другими словами, при аренде и покупке кондоминиумов существует не так много ограничений и правил.

    Самое главное, что следует иметь в виду, рассматривая кондоминиум, - это то, что право собственности на здание и право собственности на землю могут быть разделены и не принадлежать владельцу. Как уже упоминалось выше, жилая часть кондоминиума - это CoOp, то есть компания, владеющая недвижимостью, но часто компания, владеющая недвижимостью в кондоминиуме, владеет только недвижимостью над землей, а земля арендуется, что мы называем ленд-лизом. Многие люди, купившие Кондоп в прошлом, сталкиваются с растущими ежемесячными расходами, которые выше, чем у других местных объектов недвижимости, что приводит к значительному снижению стоимости и становится бременем.

    (Хотя строительство на условиях ленд-лиза наиболее распространено в Кондопе, есть и такие кондоминиумы, где земля арендуется, так что имейте это в виду).
                """)
    
    st.image('Photos/condop.jpeg', caption = 'Фотография Condop')


    st.header('Townhouse (Таунхаус)')

    st.markdown("""
    Таунхаусы можно разделить на кондоминиумы, односемейные и многосемейные.
    Проще говоря

    Таунхаус кондо - это многоквартирный дом, принадлежащий разным владельцам, и при покупке, продаже или сдаче в аренду он следует обычному процессу кондоминиума.

    Односемейный таунхаус - это целое здание, принадлежащее одному владельцу с одной законной кухней. При аренде и продаже не нужно подавать никаких заявлений, потому что здесь нет совета соседей, требуется только согласие владельца.

    Таунхаус Multi-Family принадлежит одному владельцу, но имеет несколько законных кухонь, и по закону может сдаваться в аренду нескольким семьям. В случае аренды и продажи, поскольку нет комитета по управлению домом, не требуется никаких заявлений, только согласие владельца дома.
                """)
    
    st.image('Photos/townhouse.jpeg', caption = 'Фотография Townhouse')


    st.header('Land (Земельный участок)')

    st.markdown("""
    Земельные участки в Нью-Йорке представляют собой особую категорию недвижимости в городе. Ввиду ограниченности пространства и высокой плотности застройки, доступные земельные участки в городе могут быть редкими и ценными. Однако возможности приобретения земли в Нью-Йорке все же существуют, особенно в некоторых пригородных районах и за пределами города.
                """)
    
    st.image('Photos/land.jpeg', caption = 'Фотография Land')














###------------------------------------------------------------------------------------------------------------------------------
### Главное    
elif selected == "Главное":
    st.header('Пет-проект по прогнозированию цен на недвижимость в Нью-Йорке и её кластеризации')
    st.markdown('Автор пет-проекта <a href="https://github.com/000p1umDiesel" target="_blank">ссылка</a>', unsafe_allow_html=True)


    st.header('Введение')
    st.write('Данный пет-проект посвящён анализу недвижимости в Нью-Йорке с целью прогнозирования цен и её кластеризации для выявления характерных классов объектов.')

    st.header('Цель проекта')
    st.write('- Разработка модели прогнозирования цен на недвижимость в Нью-Йорке.')
    st.write('- Кластеризация недвижимости для выявления основных классов объектов по их характеристикам.')
    st.write('- Разработка веб-сервиса для расчёта цены недвижимости в Нью-Йорке по выбраным параметрам')

    st.header('Этапы проекта')

    st.subheader('Сбор данных')
    st.write('- Процесс сбора и очистки данных.')

    st.subheader('Исследовательский анализ данных (EDA)')
    st.write('- Визуализация основных характеристик недвижимости.')
    st.write('- Анализ корреляций и трендов.')

    st.subheader('Прогнозирование цен')
    st.write('- Подготовка данных и выбор модели машинного обучения.')
    st.write('- Обучение модели и оценка её качества.')

    st.subheader('Кластеризация недвижимости')
    st.write('- Подготовка данных и выбор метода кластеризации.')
    st.write('- Кластеризация недвижимости и анализ полученных кластеров.')

    st.header('Визуализация и результаты')
    st.write('Представление результатов прогнозирования и кластеризации с использованием Streamlit.')














###------------------------------------------------------------------------------------------------------------------------------
### Отображение карты со свободной недвижимостью
elif selected == 'Карта свободной недвижимости':
    st.title('Карта свободной недвижимости (100 объектов)')

    df1 = pd.read_excel('X_example.xlsx')
    df1.drop('Unnamed: 0', axis=1, inplace=True)

    df2 = pd.read_csv('NY-House-Dataset.csv')
    df2 = df2[['LATITUDE', 'LONGITUDE']]

    df = df1.merge(df2, left_index=True, right_index=True)

    select_options = ['Все', 'Queens', 'New York', 'Kings', 'Richmond', 'Bronx']

    district = st.selectbox('Выбрать район для отрисовки', select_options)

    my_map = folium.Map(location=[df['LATITUDE'].mean(), df['LONGITUDE'].mean()], zoom_start=10.5)

    icon_dict = {
        'Queens': ('blue', 'home'),
        'New York': ('red', 'home'),
        'Kings': ('green', 'home'),
        'Richmond': ('orange', 'home'),
        'Bronx': ('purple', 'info-home')
    }

    if district == 'Все':
        for index, row in df.head(100).iterrows():
            folium.Marker(
                location=[row['LATITUDE'], row['LONGITUDE']],
                popup=f"Цена: {row['PRICE']}, Район: {row['District']}, Тип: {row['TYPE']}, Площадь",
                icon=folium.Icon(color='gray', icon='home') 
            ).add_to(my_map)
    else:
        filtered_df = df[df['District'] == district]
        color, icon = icon_dict.get(district, ('gray', 'home')) 
        for index, row in filtered_df.head(100).iterrows():
            folium.Marker(
                location=[row['LATITUDE'], row['LONGITUDE']],
                popup=f"Цена: {row['PRICE']}, Район: {row['District']}, Тип: {row['TYPE']}, Площадь",
                icon=folium.Icon(color=color, icon=icon)  
            ).add_to(my_map)

    st_folium(my_map, width=700, height=700, use_container_width=True)















###------------------------------------------------------------------------------------------------------------------------------
### Про модели
elif selected == 'Модели':
    st.title('Модели, применяемые для прогнозирования стоимости недвижимости и кластеризации')

    st.header('Catboost')
    st.subheader('Параметры')

    st.markdown("""
                - depth = 7
                - iterations = 500
                - learning rate = 0.1""")
    
    st.subheader('Метрики')

    st.markdown("""
                - MAE = 469768.38
                - MSE 853486762537.58
                - r2 = 0.711
                """)
    
    st.header('K-Means')
    st.subheader('Параметры')

    st.markdown('- n_clusters = 4')

    st.subheader('Метрики')

    st.markdown("""
                - Silhouette Score = 0.20
                - Davies-Bouldin Index = 1.77
                - Calinski-Harabasz Index = 1453.63
                """)















###------------------------------------------------------------------------------------------------------------------------------
### Про Нью-Йорк и районы
elif selected == 'Нью Йорк и его районы':
    st.header('Нью Йорк и его районы')

    st.subheader('Нью Йорк')

    st.markdown("""
    Нью-Йорк — крупнейший город США, входящий в одну из крупнейших агломераций мира. Население города составляет 8 467 513 человек, агломерации — 19,77 млн (оценка на 2021 год). Нью-Йорк расположен на берегу Атлантического океана в юго-восточной части штата Нью-Йорк. Город был основан в начале XVII века голландскими колонистами и до 1664 года назывался Новый Амстердам.
    Нью-Йорк включает пять административных округов (районов, боро): Бронкс, Бруклин, Куинс, Манхэттен и Статен-Айленд. Основные достопримечательности расположены в боро Манхэттен. Среди них: исторические небоскрёбы (Эмпайр-стейт-билдинг, Крайслер-билдинг), Рокфеллеровский центр, Вулворт-билдинг, художественный Метрополитен-музей, Метрополитен-опера, Карнеги-холл, Музей Соломона Гуггенхейма (живопись), Американский музей естественной истории (скелеты динозавров и планетарий), отель «Плаза», отель «Уолдорф-Астория», отель «Челси», штаб-квартира ООН, Гарлем.
    Нью-Йорк — важный мировой финансовый, политический, экономический и культурный центр.
    """)

    st.image('Photos/new_york.jpg', caption = 'Фотография Нью-Йорк')

    st.subheader('Бронкс')

    st.markdown("""
    Бронкс — одно из пяти боро Нью-Йорка, единственное, чья территория находится на континентальной части суши, и единственное с определённым артиклем в официальном английском названии.

    Почти вся территория Бронкса расположена в континентальной части США. Бронкс расположен на севере города, от Манхэттена его отделяет пролив Харлем, от Куинса — Ист-Ривер. Река Гудзон отделяет Бронкс от боро Алпайн, Тенафлай и Инглвуд-Клиффс в округе Берген штата Нью-Джерси. Проливом Лонг-Айленд Бронкс отделяется от округа Нассо. К северу от Бронкса расположены пригороды Нью-Йорка Йонкерс, Маунт-Вернон, Пелем-Манор и Нью-Рошелл. На юге Бронкса расположен район Марбл-Хилл, который формально является частью боро Манхэттен, однако его ZIP- и телефонный коды относятся к Бронксу.
    Самая высокая точка Бронкса расположена на его северо-западе в Ван-Кортландт-парке. Её высота составляет 85 метров.
    """)

    st.image('Photos/bronx.jpeg', caption = 'Фотография Бронкс')

    st.subheader('Бруклин')

    st.markdown("""
    Бруклин — второй по популярности район в Нью-Йорке после Манхэттена, в котором проживает 2,5 миллиона человек, их количество растет — от состоятельных граждан, подыскивающих величественные особняки в Кэрролл Гарденс (Carroll Gardens), до молодых участников музыкальных групп, соблазненных дешевой арендной платой в Вильямсбурге (Williamsburg). По мнению многих, этот периферийный городской район с самоуправлением долго был преемником Манхэттена по части крутизны и пригодности для жилья. От песчаных пляжей и зовущих к беззаботному променаду тротуаров с одной стороны до гурманских кафе и ресторанчиков с другой, большого количества этнических кварталов, развлечений мирового класса, представительной архитектуры и нескончаемых магазинов, Бруклин составляет конкуренцию Манхэттену.
    """)

    st.image('Photos/brooklyn.jpeg', caption = 'Фотография Бруклин')

    st.subheader('Куинс')

    st.markdown("""
    Куинс — самое большое по территории (280 км²) и второе по населению после Бруклина боро Нью-Йорка. Расположено на острове Лонг-Айленд и омывается Атлантическим океаном. Это самая неоднородная по этническому составу часть города.
    
    В Куинсе находится Международный аэропорт имени Джона Кеннеди, а также аэропорт «Ла-Гуардия». В Куинсе базируется бейсбольная команда «Нью-Йорк Метс», проходит Открытый чемпионат США по теннису.
    
    По обзорам Американского общества, с 2005 года иммигранты составляют 47,6 % жителей Куинса. С населением в 2,3 миллиона человек это второй по количеству жителей округ Нью-Йорка (после Бруклина) и 10-й по плотности населения округ в Соединённых Штатах. Если бы каждый район Нью-Йорка стал независимым городом, то Бруклин и Куинс стали бы третьим и четвёртым городами по численности населения в США, уступая Лос-Анджелесу и Чикаго.

    Район традиционно считается одним из более «пригородных» районов Нью-Йорка, окрестности в восточном Куинсе больше напоминают окрестности округа Нассау в штате Нью-Йорк в своей северо-западной части. В боро имеется несколько деловых кварталов, таких как Лонг-Айленд-Сити на береговой линии Куинса напротив Манхэттена.
    """)

    st.image('Photos/queens.jpeg', caption = 'Фотография Куинс')

    st.subheader('Статен-Айленд')

    st.markdown("""
    Статен-Айленд — одно из пяти боро Нью-Йорка, расположенное на острове Статен. Наиболее территориально удалённый и наименее населённый из всех административных округов Нью-Йорка. Самая южная часть штата Нью-Йорк. Территориально совпадает с округом Ричмонд и поэтому вплоть до 1975 года район назывался Ричмонд. Статен-Айленд стал боро Нью-Йорка в 1898 году.
    
    На Статен-Айленде с 1947 года находилась городская свалка, которая закрылась лишь в 2001 году. Сейчас ведутся работы по рекультивации территории для создания зон отдыха и развлечений.

    Статен-Айленд считается «спальным» районом Нью-Йорка. По сравнению с другими районами (Бронксом, Бруклином, Манхэттеном и Куинсом), жизнь здесь спокойнее: до 1960 года в южной части острова располагались фермерские хозяйства. После постройки моста Веррацано, связавшего Статен-Айленд с Бруклином, началось его активное заселение. На улицах стало больше транспорта, дорожных пробок, аварий и дорожных работ. Тем не менее, район считается одним из самых привлекательных для горожан, особенно русскоговорящих, которых здесь насчитывается до 20 %.

    О некоторых нюансах жизни на этом острове в 2009 году режиссёром Джеймсом ДеМонако был снят художественный фильм «Статен-Айленд» (англ. Staten Island).
    """)

    st.image('Photos/staten_island.jpeg', caption = 'Фотография Статен-Айленд')


    st.subheader('Манхэттен')

    st.markdown("""
    Манхэ́ттен — историческое ядро города Нью-Йорка и одно из его пяти боро. Кроме острова Манхэттен, боро включает в себя несколько небольших островов (см. География Манхэттена).
    Площадь округа Нью-Йорк, в который входит Манхэттен — 59,47 км². Площадь же острова Манхэттен составляет 58,8 км², а население — 1,619 миллиона человек (по данным на 2012 год). Это один из самых маленьких и самый густонаселённый из округов США.
    В боро Манхэттен расположены высочайшие небоскрёбы, среди которых Всемирный торговый центр 1, Эмпайр-стейт-билдинг, Крайслер-билдинг, Вулворт-билдинг, Метлайф-тауэр, Уолл-стрит, 40, Рокфеллеровский центр.
    """)

    st.image('Photos/manhattan.jpg', caption = 'Фотография Манхэттен')














###------------------------------------------------------------------------------------------------------------------------------
### Анализ недвижимости Нью-Йорка
elif selected == 'Анализ недвижимости Нью-Йорка':

    st.header('Анализ недвижимости Нью-Йорка')

    st.markdown("""
    При покупке недвижимости в Нью-Йорке, анализ является ключевым шагом для принятия обоснованных решений. Цена недвижимости может значительно варьироваться в зависимости от различных параметров, и глубокий анализ поможет определить оптимальное соотношение цены и качества.

    Первым и, возможно, наиболее важным фактором является расположение. В Нью-Йорке каждый район имеет свои особенности и преимущества, отражающиеся в цене недвижимости. Районы с развитой инфраструктурой, близостью к деловым центрам и хорошими школами обычно имеют более высокие цены, чем более удаленные районы или те, которые испытывают социальные или экономические проблемы.

    Тип недвижимости также оказывает существенное влияние на цену. Квартиры в многоэтажных домах, таунхаусы, частные дома — каждый из этих типов имеет свои уникальные характеристики и стоимость. Квартиры, например, часто более доступны по цене, но требуют платы за обслуживание и имеют ограниченное пространство по сравнению с домами.

    В конце концов, для принятия осознанного решения необходимо обращаться к статистическим данным. Внизу представлена небольшая сводная статистика по недвижимости в Нью-Йорке, которая может помочь вам лучше понять текущее состояние рынка и сделать более обоснованный выбор.
    """)

    def fast_kmeans():

        data = pd.read_excel('X_example.xlsx').drop('Unnamed: 0', axis=1)
        data = pd.get_dummies(data, columns=['District', 'TYPE'], drop_first=True, prefix=None)
        temp_data = pd.read_excel('X_example.xlsx').drop('Unnamed: 0', axis=1)

        temp_data = temp_data[['TYPE', 'District', 'Close to the sights']]

        model_kmeans = joblib.load('Kmeans.pkl')
        clusters = model_kmeans.predict(data)

        data['cluster'] = clusters

        mean_df = data.groupby('cluster').mean()
        elite_category_kmeans = mean_df['PRICE'].idxmax()
        economic_category_kmeans = mean_df['PRICE'].idxmin()
        comfort_category_kmeans = mean_df[mean_df['PRICE'] > mean_df['PRICE'].loc[economic_category_kmeans]].idxmin()['PRICE']
        business_category_kmeans = mean_df[mean_df['PRICE'] < mean_df['PRICE'].loc[elite_category_kmeans]].idxmax()['PRICE']
        data['Класс недвижимости'] = data['cluster'].map({
            elite_category_kmeans: 'Элитный',
            economic_category_kmeans: 'Эконом',
            comfort_category_kmeans: 'Комфорт',
            business_category_kmeans: 'Бизнес'
        })


        data = data[['PRICE', 'BEDS', 'BATH', 'PROPERTYSQFT', 'Класс недвижимости']]
        data = data.merge(temp_data[['TYPE', 'District', 'Close to the sights']], left_index=True, right_index=True)

        return data
    
    data = fast_kmeans()


### Визуал 
    fig = px.pie(
        data.groupby('Класс недвижимости')['PRICE'].count().reset_index().rename(columns={'PRICE' : 'Количество объектов'}),
        names='Класс недвижимости', title = 'Распределение количества объектов недвижимости по классам', values='Количество объектов')

    st.plotly_chart(fig, theme='streamlit', use_container_width=True)

    fig = px.pie(
        data.groupby('TYPE')['PRICE'].count().reset_index().rename(columns={'PRICE' : 'Количество объектов'}),
        names='TYPE', values='Количество объектов', title = 'Распределение количества объектов недвижимости по видам')

    st.plotly_chart(fig, theme='streamlit', use_container_width=True)


    st.subheader('Нью-Йорк')

    fig = px.bar(data[data['District'] == 'New York'].groupby('Класс недвижимости')['PRICE'].mean().reset_index(),
        x='Класс недвижимости', y='PRICE',color='Класс недвижимости', title = 'Средняя цена на недвижимость в Нью-Йорке в зависимости от класса недвижимости')

    st.plotly_chart(fig, theme='streamlit', use_container_width=True)


    fig = px.bar(data[data['District'] == 'New York'].groupby('TYPE')['PRICE'].mean().reset_index(),
        x='TYPE', y='PRICE', color='TYPE', title = 'Средняя цена на недвижимость в Нью-Йорке в зависимости от вида недвижимости')

    st.plotly_chart(fig, theme='streamlit', use_container_width=True)


    st.subheader('Бронкс')

    fig = px.bar(data[data['District'] == 'Bronx'].groupby('Класс недвижимости')['PRICE'].mean().reset_index(),
        x='Класс недвижимости', y='PRICE',color='Класс недвижимости', title = 'Средняя цена на недвижимость в Бронксе в зависимости от класса недвижимости')

    st.plotly_chart(fig, theme='streamlit', use_container_width=True)

    fig = px.bar(data[data['District'] == 'Bronx'].groupby('TYPE')['PRICE'].mean().reset_index(),
        x='TYPE', y='PRICE',color='TYPE', title = 'Средняя цена на недвижимость в Бронксе в зависимости от вида недвижимости')

    st.plotly_chart(fig, theme='streamlit', use_container_width=True)


    st.subheader('Кингс')

    fig = px.bar(data[data['District'] == 'Kings'].groupby('Класс недвижимости')['PRICE'].mean().reset_index(),
        x='Класс недвижимости', y='PRICE',color='Класс недвижимости', title = 'Средняя цена на недвижимость в Кингсе в зависимости от класса недвижимости')

    st.plotly_chart(fig, theme='streamlit', use_container_width=True)

    fig = px.bar(data[data['District'] == 'Kings'].groupby('TYPE')['PRICE'].mean().reset_index(),
        x='TYPE', y='PRICE',color='TYPE', title = 'Средняя цена на недвижимость в Кингсе в зависимости от вида недвижимости')

    st.plotly_chart(fig, theme='streamlit', use_container_width=True)


    st.subheader('Ричмонд')

    fig = px.bar(data[data['District'] == 'Richmond'].groupby('Класс недвижимости')['PRICE'].mean().reset_index(),
        x='Класс недвижимости', y='PRICE',color='Класс недвижимости', title = 'Средняя цена на недвижимость в Ричмонде в зависимости от класса недвижимости')

    st.plotly_chart(fig, theme='streamlit', use_container_width=True)

    fig = px.bar(data[data['District'] == 'Richmond'].groupby('TYPE')['PRICE'].mean().reset_index(),
        x='TYPE', y='PRICE',color='TYPE', title = 'Средняя цена на недвижимость в Ричмонде в зависимости от вида недвижимости')

    st.plotly_chart(fig, theme='streamlit', use_container_width=True)


    st.subheader('Куинс')

    fig = px.bar(data[data['District'] == 'Queens'].groupby('Класс недвижимости')['PRICE'].mean().reset_index(),
        x='Класс недвижимости', y='PRICE',color='Класс недвижимости', title = 'Средняя цена на недвижимость в Куинсе в зависимости от класса недвижимости')

    st.plotly_chart(fig, theme='streamlit', use_container_width=True)

    fig = px.bar(data[data['District'] == 'Queens'].groupby('TYPE')['PRICE'].mean().reset_index(),
        x='TYPE', y='PRICE',color='TYPE', title = 'Средняя цена на недвижимость в Куинсе в зависимости от вида недвижимости')

    st.plotly_chart(fig, theme='streamlit', use_container_width=True)














###------------------------------------------------------------------------------------------------------------------------------
### Подбор квартиры 
elif selected == 'Подобрать недвижимость':
    st.header('Подбор недвижимости в зависимости от параметров')

    def fast_kmeans():

        data = pd.read_excel('X_example.xlsx').drop('Unnamed: 0', axis=1)
        data = pd.get_dummies(data, columns=['District', 'TYPE'], drop_first=True, prefix=None)
        temp_data = pd.read_excel('X_example.xlsx').drop('Unnamed: 0', axis=1)
        coordinates = pd.read_csv('NY-House-Dataset.csv')
        coordinates = coordinates[['LATITUDE', 'LONGITUDE']]

        temp_data = temp_data[['TYPE', 'District', 'Close to the sights']]

        model_kmeans = joblib.load('Kmeans.pkl')
        clusters = model_kmeans.predict(data)

        data['cluster'] = clusters

        mean_df = data.groupby('cluster').mean()
        elite_category_kmeans = mean_df['PRICE'].idxmax()
        economic_category_kmeans = mean_df['PRICE'].idxmin()
        comfort_category_kmeans = mean_df[mean_df['PRICE'] > mean_df['PRICE'].loc[economic_category_kmeans]].idxmin()['PRICE']
        business_category_kmeans = mean_df[mean_df['PRICE'] < mean_df['PRICE'].loc[elite_category_kmeans]].idxmax()['PRICE']
        data['Класс недвижимости'] = data['cluster'].map({
            elite_category_kmeans: 'Элитный',
            economic_category_kmeans: 'Эконом',
            comfort_category_kmeans: 'Комфорт',
            business_category_kmeans: 'Бизнес'
        })


        data = data[['PRICE', 'BEDS', 'BATH', 'PROPERTYSQFT', 'Класс недвижимости']]
        data = data.merge(temp_data[['TYPE', 'District', 'Close to the sights']], left_index=True, right_index=True)
        data = data.merge(coordinates, left_index=True, right_index=True)

        return data

    def user_input_features():
        type_options = ['Любой', 'Co-op', 'House', 'Condo', 'Multi-family home', 'Condop', 'Townhouse', 'Land']
        district_options = ['Любой', 'Queens', 'New York', 'Kings', 'Richmond', 'Bronx']
        class_options = ['Любой', 'Эконом', 'Комфорт', 'Бизнес', 'Элитный']
        close_to_sights_options = ['Любой', 'Да', 'Нет']

        type = st.selectbox('Выберите тип дома', type_options)
        
        if type == 'Land':
            district = st.selectbox('Район', district_options)
            close_to_sights = st.selectbox('Близость к достопримечательностям', close_to_sights_options)
            close_to_sights = None if close_to_sights == 'Любой' else (1 if close_to_sights == 'Да' else 0)
            class_estate = st.selectbox('Класс', class_options)
            price = st.slider('Выберите цену', min_value=0, max_value=15000000, step=1000)
            sqft = sqft = st.number_input('Введите размер площади в квадратных метрах', step=1, min_value=950, max_value=9999)

            return price, None, None, sqft, district, close_to_sights, class_estate, type

        else:
            price = st.slider('Выберите цену', min_value=0, max_value=15000000, step=1000)
            bed = st.number_input('Введите количество спальных комнат', step=1, min_value=1, max_value=100)
            bath = st.number_input('Введите количество ванных комнат', step=1, min_value=1, max_value=100)
            sqft = st.number_input('Введите размер площади в квадратных метрах', step=1, min_value=20, max_value=9999)
            district = st.selectbox('Район', district_options)
            class_estate = st.selectbox('Класс', class_options)
            close_to_sights = st.selectbox('Близость к достопримечательностям', close_to_sights_options)
            close_to_sights = None if close_to_sights == 'Любой' else (1 if close_to_sights == 'Да' else 0)
        
            return price, bed, bath, sqft, district, close_to_sights, class_estate, type

    price, bed, bath, sqft, district, close_to_sights, class_estate, type = user_input_features()

    data = fast_kmeans()

    if type != 'Land':
        min_sqft = sqft * 0.9  # Нижний предел - 90% от исходного значения sqft
        max_sqft = sqft  # Верхний предел - исходное значение sqft
        condition = (data['BEDS'] == bed) & \
                    (data['BATH'] == bath) & \
                    ((data['PROPERTYSQFT'] >= min_sqft) & (data['PROPERTYSQFT'] <= max_sqft)) & \
                    (data['PRICE'] <= price)
                    
        if class_estate != 'Любой':
            condition &= (data['Класс недвижимости'] == class_estate)
        
        if type != 'Любой':
            condition &= (data['TYPE'] == type)
        
        if district != 'Любой':
            condition &= (data['District'] == district)

        if close_to_sights is not None: 
            condition &= (data['Close to the sights'] == close_to_sights)

        similar_rows = data.loc[condition]

    else:

        condition = (data['PRICE'] <= price)
    
        if type != 'Любой':
            condition &= (data['TYPE'] == type)

        if class_estate != 'Любой':
            condition &= (data['Класс недвижимости'] == class_estate)

        if district != 'Любой':
            condition &= (data['District'] == district)

        if close_to_sights is not None: 
            condition &= (data['Close to the sights'] == close_to_sights)
        
        similar_rows = data.loc[condition]
        similar_rows = similar_rows.drop(['BEDS', 'BATH'], axis = 1)

    if not similar_rows.empty:
        my_map = folium.Map(location=[similar_rows['LATITUDE'].mean(), similar_rows['LONGITUDE'].mean()], zoom_start=10.5)

        for index, row in similar_rows.head(100).iterrows():
            popup = f"Цена: {row['PRICE']}, Район: {row['District']}, Тип: {row['TYPE']}"
            folium.Marker(
                location=[row['LATITUDE'], row['LONGITUDE']],
                popup=popup,
                icon=folium.Icon(color='green', icon='home')
            ).add_to(my_map)

        similar_rows = similar_rows.drop(['LATITUDE', 'LONGITUDE'], axis = 1)
        similar_rows['Close to the sights'] = similar_rows['Close to the sights'].map({1: 'Да', 0: 'Нет'})
        similar_rows = similar_rows.reset_index().drop('index', axis =1)
        
        similar_rows = similar_rows.rename(columns = {'PRICE' : 'Цена', 'BEDS' : 'Кол-во спальных комнат',
                                                      'BATH' : 'Кол-во ванных комнат', 'PROPERTYSQFT' : 'Площадь (квадратные метры)',
                                                      'TYPE' : 'Тип недвижимости', 'District' : 'Район',
                                                      'Close to the sights' : 'Близость к достопримичательностям'})

        st.dataframe(similar_rows)    

        folium_static(my_map, width=700, height=700)
    else:
        st.warning('Нет подходящей недвижимости')
