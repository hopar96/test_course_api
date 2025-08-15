#!/bin/bash

# --- 데이터베이스 접속 정보 ---
DB_USER="examuser"
DB_NAME="examdb"
DB_IMAGE_NAME="exam_cource_api-db-1"

# --- SQL 쿼리 작성 ---
# -- SQL 문자열 내에서 셸 변수를 사용하기 위해 작은따옴표를 섞어 사용합니다.
SQL_QUERY="DO \$\$
DECLARE
    -- 임의의 시작 시간을 저장할 변수
    start_time timestamp;

BEGIN
    TRUNCATE TABLE api_tag RESTART IDENTITY CASCADE;
    TRUNCATE TABLE api_course_tags RESTART IDENTITY CASCADE;
    TRUNCATE TABLE api_course RESTART IDENTITY CASCADE;
    TRUNCATE TABLE api_test RESTART IDENTITY CASCADE;
    insert into api_tag (name) values ('파이썬'), ('장고'), ('데이터 분석'), ('백엔드'), ('프론트엔드'), ('코틀린'), ('자바'),('스프링'),('알고리즘'),('추천');

    FOR i IN 1..5000 LOOP
        -- 시작 시간을 현재 시간 기준으로 -15일부터 +15일까지 랜덤하게 설정
        start_time := NOW() + (random() * 30 - 15) * '1 day'::interval;

        INSERT INTO api_test (
            created_at,
            updated_at,
            title,
            description,
            start_at,
            end_at,
            popularity,
            price
        ) VALUES (
            NOW(),
            NOW(),
            CONCAT('시험 제목 ', i),
            CONCAT('이것은 시험 번호 ', i, '에 대한 상세 설명입니다. 내용은 동적으로 생성되었습니다.'),
            start_time,
            -- 종료 시간은 시작 시간으로부터 1~6시간 뒤로 랜덤하게 설정
            start_time + (random() * 5 + 1) * '1 hour'::interval,
            0, -- 인기도
            floor(random() * 20 + 1) * 5000 -- 가격 50,000 ~ 100,000 (5,000원 단위)
        );

        INSERT INTO api_course (
            created_at,
            updated_at,
            title,
            description,
            start_at,
            end_at,
            popularity,
            price
        ) VALUES (
            NOW(),
            NOW(),
            CONCAT('수업 제목 ', i),
            CONCAT('이것은 수업 번호 ', i, '에 대한 상세 설명입니다. 내용은 동적으로 생성되었습니다.'),
            start_time,
            start_time + (random() * 20 + 10) * '1 day'::interval, -- 수업 기간은 10~30일
            0, -- 인기도
            floor(random() * 30 + 1) * 10000 -- 가격 100,000 ~ 300,000 (10,000원 단위)
        );
        
        insert into api_course_tags (course_id, tag_id) values (i, i % 10 + 1);
    END LOOP;
END \$\$;




"

echo "데이터베이스 '$DB_NAME'에 연결하여 데이터 삽입 중..."

# --- psql 명령어 실행 ---
# -- -h: 호스트, -p: 포트, -U: 사용자, -d: 데이터베이스
# -- -c: 실행할 SQL 쿼리

docker exec -t ${DB_IMAGE_NAME} psql -U "${DB_USER}" -d ${DB_NAME} -c "${SQL_QUERY}"

# --- 실행 결과 확인 ---
if [ $? -eq 0 ]; then
    echo "데이터 삽입 성공"
else
    echo "데이터 삽입 실패"
fi

