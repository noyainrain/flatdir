# TODO

"""TODO."""

from .directory import Company

# TODO rename Company()
COMPANIES = [
    # Companys
    #Company(
    #    'https://www.schacher-immobilien.de/angebote/wohnungen/?mt=67555823520346',
    #    ".//*[@class='listEntry listEntryClickable listEntryObject-immoobject listEntryObject-immoobject_var']",
    #    'div/div[2]/div[2]/a',
    #    'div/div[2]/div[2]/a',
    #    'div/div[2]/div',
    #    '.',
    #    location_filter='Berlin'),

    Company(
        'https://werneburg-immobilien.de/immobilien/immobilien-vermarktungsart/miete/',
        ".//div[@class='property col-sm-6 col-md-4']",
        'div/div[2]/h3/a',
        'div/div[2]/h3/a',
        'div/div[2]/div',
        'div/div[2]/div[2]/div[2]/div[2]',
        location_filter='Berlin'),

    Company(
        'https://www.homesk.de/Rent/RentalFlats',
        ".//a[@class='tile tile-sm-640px-480px tile-md-960px-480px tile-lg-1280px-480px']",
        '.',
        'div/div/div[2]/div/div/div/div/h3',
        'div/div/div[2]/div/div/div/div/p',
        'div/div/div[2]/div/div/div/div[2]/div/div/h4'),

    # Property managers
    Company(
        'https://www.berlinhaus.com/suchergebnisse/?filter_search_action[]=wohnen&advanced_city=berlin&zimmeranzahl-ab=1',
        ".//div[@class='col-md-12 listing_wrapper']",
        'div/h4/a',
        'div/h4/a',
        'div/div[2]/a',
        'div/div[4]/div[2]'),

    Company(
        url='https://www.gesobau.de/mieten/wohnungssuche.html',
        # node=".//div[@class='list_item']",
        # node=".//div[@data-id]",
        node=".//div[@id='tx-openimmo-6329']/div[2]/div[1]/div/div[1]/div",
        link_node='div/div/h3/a',
        title_node='div/div/h3/a',
        location_node='div/div/div[1]',
        rooms_node='div/div/div[2]/div[3]'
    ),

    Company(
        'https://www.howoge.de/?type=999&tx_howsite_json_list[action]=immoList',
        'immoobjects.*',
        'link',
        'title',
        'district',
        'rooms'
        # 'https://www.howoge.de/wohnungen-gewerbe/wohnungssuche.html',
        #".//div[@class='flat-single']",
        #'div[2]/div[3]/a',
        #'div[2]/div[3]/a',
        #'div[2]/div[2]',
        #'div[2]/div[4]/div/div/div[3]/div[2]'
    ),

    Company(
        url='https://www.kurtzke-immobilien.de/objekttyp/mietwohnung/',
        node=".//div[@class='item-listing-wrap hz-item-gallery-js card']",
        link_node='div/div/div[2]/h2/a',
        title_node='div/div/div[2]/h2/a',
        location_node='div/div/div[2]/address',
        rooms_node='div/div/div[2]/ul/li/span[2]'
    ),

    Company(
        'https://www.livinginberlin.de/angebote/mieten',
        ".//div[@class='uk-container uk-margin-large-top uk-margin-medium-bottom']/div/div",
        'div/div/a',
        'div/div[2]/p',
        'div/div[2]/h3',
        'div/div[2]/span/tail()',
        location_filter='Berlin'
    )
]
