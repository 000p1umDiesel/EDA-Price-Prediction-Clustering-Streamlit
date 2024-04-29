import streamlit as st
from streamlit_option_menu import option_menu
import joblib
import pandas as pd
import folium
from streamlit_folium import st_folium

selected = option_menu('Недвижимость Нью-Йорка', ["Главное", "Виды недвижимости Нью-Йорка", "Карта свободной недвижимости","Рассчитать стоимость и определить класс", 'Модели'], 
        icons=['briefcase', 'house', 'cloud','cash','gear'], menu_icon = 'cast', 
        default_index=0, orientation="horizontal")




### Построение модели прогноза
if selected == 'Рассчитать стоимость и определить класс':
    def user_input_features():
        type_options = ('Co-op', 'House', 'Condo', 'Multi-family home', 'Condop', 'Townhouse', 'Land')
        district_options = ('Queens', 'New York', 'Kings', 'Richmond', 'Bronx')

        type = st.sidebar.selectbox('Выберете тип дома', type_options)
        
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
            bed = st.sidebar.number_input('Введите количество спальных комнат', step=1, min_value=1, max_value=100)
            bath = st.sidebar.number_input('Введите количество ванных комнат', step=1, min_value=1, max_value=100)
            sqft = st.sidebar.number_input('Введите размер площади в квадратных метрах', step=1, min_value=1, max_value=9999)
            district = st.sidebar.selectbox('Район', district_options)
            close_to_sights = st.sidebar.selectbox('Близость к достопримечательностям', ('Да', 'Нет'))
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




### Отображение карты со свободной недвижимостью
elif selected == 'Карта свободной недвижимости':
    st.title('Карта свободной недвижимости (100 объектов)')
    df = pd.read_csv('NY-House-Dataset.csv')
    my_map = folium.Map(location=[df['LATITUDE'].mean(), df['LONGITUDE'].mean()], zoom_start=10.5)

    for index, row in df.head(100).iterrows():
        folium.Marker(
            location=[row['LATITUDE'], row['LONGITUDE']],
            popup=f"{row['STREET_NAME']}\nЦена: {row['PRICE']}",
            icon=folium.Icon(color='green', icon='home')
        ).add_to(my_map)

    st_folium(my_map, width = 1500, height = 700, use_container_width = True)




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

