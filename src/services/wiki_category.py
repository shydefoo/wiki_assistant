from db_setup.DBConnect import DBConnect
from utils.wiki_logger import WikiLogger

logger = WikiLogger(__name__).logger
db_instance = DBConnect()


def find_pages_under_cat(category):
    query = """SELECT t2.page_id, rev_table.rev_timestamp
            FROM 
            (SELECT cl.cl_from as cl_from FROM categorylinks cl WHERE cl.cl_to = %s) t1
            JOIN
            (SELECT p.page_id, p.page_title, p.page_latest FROM page p) t2
            ON t2.page_id = t1.cl_from
            JOIN
            (SELECT rev.rev_timestamp, rev.rev_id FROM revision rev) rev_table 
            ON rev_table.rev_id = t2.page_latest; """

    db_instance.cursor.execute(query, (category,))
    page_ids = []
    time_stamp = []
    outdatedness_list = []
    for item in db_instance.cursor:
        page_ids.append(item[0])
        time_stamp.append(int(item[1]))
    logger.debug("page_ids: {}, len: {}".format(page_ids, len(page_ids)))
    logger.debug("timestamp: {}, len: {}".format(time_stamp, len(time_stamp)))

    for page, timestamp in zip(page_ids, time_stamp):
        outdatedness = 0

        find_links = 'SELECT page_id, page_latest ' \
                     'FROM page ' \
                     'WHERE page_title IN ' \
                     '(SELECT pl_title FROM pagelinks WHERE pl_from = %s)'
        db_instance.cursor.execute(find_links, (page,))
        links = db_instance.cursor.fetchall()
        if len(links) > 0:
            new_link = []
            for link in links:
                get_timestamp = 'SELECT rev_timestamp ' \
                                'FROM revision ' \
                                'WHERE rev_id = %s'
                db_instance.cursor.execute(get_timestamp, (link[1],))
                link_timestamp = db_instance.cursor.fetchall()
                if len(link_timestamp) > 0:
                    link_timestamp = int(link_timestamp[0][0])
                    new_link.append([link[0], link_timestamp])
                    diff = link_timestamp - timestamp  # modified later means link_timestamp > timestamp i.e diff > 0
                    outdatedness = max(outdatedness, diff)
        outdatedness_list.append(outdatedness)
    logger.debug(outdatedness_list)
    outdated_page = page_ids[outdatedness_list.index(max(outdatedness_list))]
    db_instance.cursor.execute('SELECT page_title FROM page WHERE page_id = %s', (outdated_page,))
    page = db_instance.cursor.fetchone()
    page = str(page[0], 'utf-8')
    logger.debug(page)
    return page


def find_outdatedness_sql(category):
    category = category.replace(' ', '_')
    query = """
    SELECT page_title, outdatedness
FROM page
INNER JOIN
(
	SELECT pl_from, outdatedness 
	FROM (
	    SELECT pl_from, max_rev_timestamp-rev_timestamp as outdatedness
	    FROM(
	        SELECT pl_from, max(rev_timestamp_link) as max_rev_timestamp
	        FROM
	        (
	            SELECT pl_from, page_id, rev_timestamp as rev_timestamp_link
	            FROM
	            (
	                SELECT pl_from, page_id, page_latest
	                FROM page 
	                INNER JOIN 
	                (
	                    SELECT pl_from, pl_title, pl_namespace, pl_from_namespace
	                    FROM pagelinks 
	                    WHERE pl_from in (
	                        SELECT page_id FROM (
								SELECT t1.page_id
								FROM(
									SELECT page.page_id, page.page_title, page.page_latest 
									FROM page 
									WHERE page_id in( 
										SELECT cl_from FROM categorylinks where cl_to = %s 
									)
								) t1 
							)t2_1
	                    )
	                )t3
	                ON t3.pl_title = page.page_title and page.page_namespace = t3.pl_namespace
	            )t4
	            INNER JOIN
	            (
	                SELECT rev_page, rev_timestamp 
	                FROM revision
	            )t5
	            ON t5.rev_page = t4.page_id
	        ) t6
	        GROUP BY pl_from
	    ) t7
	    INNER JOIN
	    (
	        SELECT page_id, rev_timestamp
	        FROM (
				SELECT t1.page_id, t2.rev_timestamp
				FROM
					(SELECT page.page_id, page.page_title, page.page_latest 
					FROM page 
					WHERE page_id in( 
						SELECT cl_from FROM categorylinks where cl_to = %s
					)) t1 
				INNER JOIN (
						SELECT rev_timestamp, rev_id FROM revision
					)t2 
				ON rev_id = page_latest
			)t2_1
	    ) t8 
	    on t7.pl_from = t8.page_id
	)t10
	WHERE outdatedness in (
	    SELECT max(outdatedness) as maximum_outdated
	    FROM
	    (
	        SELECT pl_from, max_rev_timestamp-rev_timestamp as outdatedness
		    FROM(
		        SELECT pl_from, max(rev_timestamp_link) as max_rev_timestamp
		        FROM
		        (
		            SELECT pl_from, page_id, rev_timestamp as rev_timestamp_link
		            FROM
		            (
		                SELECT pl_from, page_id, page_latest
		                FROM page 
		                INNER JOIN 
		                (
		                    SELECT pl_from, pl_title, pl_namespace, pl_from_namespace
		                    FROM pagelinks 
		                    WHERE pl_from in (
		                        SELECT page_id FROM (
									SELECT t1.page_id
									FROM(
										SELECT page.page_id, page.page_title, page.page_latest 
										FROM page 
										WHERE page_id in( 
											SELECT cl_from FROM categorylinks where cl_to = %s
										)
									) t1 
								)t2_1
		                    )
		                )t3
		                ON t3.pl_title = page.page_title and page.page_namespace = t3.pl_namespace
		            )t4
		            INNER JOIN
		            (
		                SELECT rev_page, rev_timestamp 
		                FROM revision
		            )t5
		            ON t5.rev_page = t4.page_id
		        ) t6
		        GROUP BY pl_from
		    ) t7
		    INNER JOIN
		    (
		        SELECT page_id, rev_timestamp
		        FROM (
					SELECT t1.page_id, t2.rev_timestamp
					FROM
						(SELECT page.page_id, page.page_title, page.page_latest 
						FROM page 
						WHERE page_id in( 
							SELECT cl_from FROM categorylinks where cl_to = %s
						)) t1 
					INNER JOIN (
							SELECT rev_timestamp, rev_id FROM revision
						)t2 
					ON rev_id = page_latest
				)t2_1
		    ) t8 
		    on t7.pl_from = t8.page_id
	    ) t9
	)
)combined
WHERE page.page_id = combined.pl_from
"""
    db_instance.cursor.execute(query, (category, category, category, category))
    result = list(map(lambda x: [str(x[0], 'utf-8'), x[1]], db_instance.cursor.fetchall()))
    return result

if __name__ == "__main__":
    # find_pages_under_cat('South_Korea')
    logger.debug(find_outdatedness_sql('Living people'))